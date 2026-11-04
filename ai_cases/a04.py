import ast
import math
import operator


_MAX_EXPR_LENGTH = 1000
_MAX_NODES = 100
_MAX_INT_BITS = 4096
_MAX_EXPONENT = 1000

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def calc(expr):
    if not isinstance(expr, str) or len(expr) > _MAX_EXPR_LENGTH:
        raise ValueError("Invalid or oversized expression")

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid expression") from exc

    if sum(1 for _ in ast.walk(tree)) > _MAX_NODES:
        raise ValueError("Expression is too complex")

    def evaluate(node):
        if isinstance(node, ast.Constant):
            value = node.value
            if type(value) not in (int, float):
                raise ValueError("Only numeric literals are allowed")
            if isinstance(value, int) and value.bit_length() > _MAX_INT_BITS:
                raise ValueError("Integer is too large")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Number must be finite")
            return value

        if isinstance(node, ast.BinOp):
            left = evaluate(node.left)
            right = evaluate(node.right)

            if isinstance(node.op, ast.Pow):
                if type(right) is not int or abs(right) > _MAX_EXPONENT:
                    raise ValueError("Exponent is out of range")
                result = operator.pow(left, right)
            else:
                operation = _BINARY_OPERATORS.get(type(node.op))
                if operation is None:
                    raise ValueError("Operator is not allowed")
                result = operation(left, right)

            if type(result) is int and result.bit_length() > _MAX_INT_BITS:
                raise ValueError("Integer result is too large")
            if type(result) is float and not math.isfinite(result):
                raise ValueError("Result must be finite")
            return result

        if isinstance(node, ast.UnaryOp):
            operation = _UNARY_OPERATORS.get(type(node.op))
            if operation is None:
                raise ValueError("Operator is not allowed")
            return operation(evaluate(node.operand))

        raise ValueError("Expression contains an unsupported operation")

    return evaluate(tree.body)
