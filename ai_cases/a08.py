import ast
import math
import operator
import sqlite3


def get_user(conn, username):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (username,))
    return cursor.fetchall()


def calc(expr):
    if not isinstance(expr, str) or len(expr) > 256:
        raise ValueError("Expression must be a string of at most 256 characters")

    tree = ast.parse(expr, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 64:
        raise ValueError("Expression is too complex")

    binary_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
    }
    unary_ops = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant):
            value = node.value
            if type(value) not in (int, float):
                raise ValueError("Only numeric literals are allowed")
            if isinstance(value, int) and value.bit_length() > 256:
                raise ValueError("Numeric value is too large")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Numeric value must be finite")
            return value

        if isinstance(node, ast.BinOp):
            operation = binary_ops.get(type(node.op))
            if operation is None:
                raise ValueError("Operator is not allowed")

            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Mult) and (
                (isinstance(left, int) and left.bit_length() > 256)
                or (isinstance(right, int) and right.bit_length() > 256)
            ):
                raise ValueError("Numeric value is too large")

            result = operation(left, right)
            if isinstance(result, int) and result.bit_length() > 256:
                raise ValueError("Numeric result is too large")
            if isinstance(result, float) and not math.isfinite(result):
                raise ValueError("Numeric result must be finite")
            return result

        if isinstance(node, ast.UnaryOp):
            operation = unary_ops.get(type(node.op))
            if operation is None:
                raise ValueError("Operator is not allowed")
            return operation(evaluate(node.operand))

        raise ValueError("Expression contains unsupported syntax")

    return evaluate(tree)
