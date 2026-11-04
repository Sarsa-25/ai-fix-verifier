import sqlite3
import ast
import operator

# Supported operators for safe mathematical expression evaluation
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def get_user(conn, username):
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE name = ?"
    cursor.execute(query, (username,))
    return cursor.fetchall()


def _eval_node(node):
    if isinstance(node, ast.Constant):  # Python 3.8+
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported literal type: {type(node.value)}")
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op_type = type(node.op)
        if op_type in OPERATORS:
            return OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported binary operator: {op_type}")
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand)
        op_type = type(node.op)
        if op_type in OPERATORS:
            return OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type}")
    else:
        raise ValueError(f"Unsupported expression node: {type(node)}")


def calc(expr):
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree.body)
