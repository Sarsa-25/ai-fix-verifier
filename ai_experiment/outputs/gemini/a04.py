import ast
import operator

# Supported mathematical operators
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


def safe_eval(node):
    """Recursively evaluates an AST node containing mathematical expressions."""
    if isinstance(node, ast.Constant) and isinstance(
        node.value, (int, float, complex)
    ):
        return node.value

    if isinstance(node, ast.BinOp):
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        op_type = type(node.op)
        if op_type in OPERATORS:
            return OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")

    if isinstance(node, ast.UnaryOp):
        operand = safe_eval(node.operand)
        op_type = type(node.op)
        if op_type in OPERATORS:
            return OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def calc(expr):
    """Safely evaluates a mathematical string expression without risk of arbitrary code execution."""
    if not isinstance(expr, str):
        raise TypeError("Expression must be a string")

    try:
        parsed_ast = ast.parse(expr, mode="eval")
        return safe_eval(parsed_ast.body)
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError) as e:
        raise ValueError(f"Invalid or unsafe expression: {expr}") from e
