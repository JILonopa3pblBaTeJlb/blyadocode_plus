#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ЭТАЛОННЫЙ ТРАНСЛЯТОР: PYTHON 3.11 -> BLYADOCODE+ (v2.0.0-PROPOSAL)
Соответствие спецификации: ISO/IEC JTC1/SC22/BLYAD-PLUS-STD-2026
"""

import ast
import sys
import argparse
from typing import Dict, List, Optional, Tuple

# Базис B4: {0: блядь, 1: хуй, 2: пизда, 3: ебать}
B4_DIGITS = {0: "блядь", 1: "хуй", 2: "пизда", 3: "ебать"}

def encode_int(n: int) -> str:
    """Кодирование целого числа в каноническую квоту пиздой ... пиздец."""
    if n == 0:
        return "пиздой блядь пиздец"
    digits = []
    v = abs(n)
    while v > 0:
        digits.append(v % 4)
        v //= 4
    digits.reverse()
    words = [B4_DIGITS[d] for d in digits]
    return f"пиздой {' '.join(words)} пиздец"

def encode_str(s: str) -> str:
    """Кодирование UTF-8 строки по 4 четверичных разряда на байт."""
    raw = s.encode("utf-8")
    tokens = ["пиздой"]
    for b in raw:
        tokens.append(B4_DIGITS[(b >> 6) & 3])
        tokens.append(B4_DIGITS[(b >> 4) & 3])
        tokens.append(B4_DIGITS[(b >> 2) & 3])
        tokens.append(B4_DIGITS[b & 3])
    tokens.append("пиздец")
    return " ".join(tokens)


class SymbolTable:
    """Таблица адресации переменных и функций в целочисленные идентификаторы."""
    def __init__(self):
        self.var_map: Dict[str, int] = {}
        self.func_map: Dict[str, int] = {}
        self.var_counter = 1
        self.func_counter = 1
        self.declared_vars = set()

    def get_var_id(self, name: str) -> int:
        if name not in self.var_map:
            self.var_map[name] = self.var_counter
            self.var_counter += 1
        return self.var_map[name]

    def get_func_id(self, name: str) -> int:
        if name not in self.func_map:
            self.func_map[name] = self.func_counter
            self.func_counter += 1
        return self.func_map[name]


class BlyadTranspiler(ast.NodeVisitor):
    def __init__(self):
        self.symbols = SymbolTable()
        self.current_scope_args: Dict[str, int] = {}  # arg_name -> arg_index
        self.lines: List[str] = []
        self.indent_level = 0
        self.temp_var_counter = 9000

    def emit(self, text: str, comment: Optional[str] = None):
        indent = "    " * self.indent_level
        c_part = f"  # {comment}" if comment else ""
        self.lines.append(f"{indent}{text}{c_part}")

    # =========================================================================
    # ВЫРАЖЕНИЯ (ПРЕФИКСНАЯ НОТАЦИЯ BLYADOCODE+)
    # =========================================================================

    def transpile_expr(self, node: ast.AST) -> str:
        # Константы (числа, строки, булевы значения)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return encode_int(1 if node.value else 0)
            elif isinstance(node.value, int):
                if node.value < 0:
                    # Отрицательные числа: (0 - |x|)
                    return f"ебатям {encode_int(0)} {encode_int(abs(node.value))}"
                return encode_int(node.value)
            elif isinstance(node.value, str):
                return encode_str(node.value)
            else:
                return encode_int(0)

        # Переменные и аргументы
        if isinstance(node, ast.Name):
            if node.id in self.current_scope_args:
                arg_idx = self.current_scope_args[node.id]
                return f"блядью {encode_int(arg_idx)}"
            else:
                var_id = self.symbols.get_var_id(node.id)
                return f"бляди {encode_int(var_id)}"

        # Бинарная арифметика
        if isinstance(node, ast.BinOp):
            left = self.transpile_expr(node.left)
            right = self.transpile_expr(node.right)
            op_map = {
                ast.Add: "ебатей",   # +
                ast.Sub: "ебатям",   # -
                ast.Mult: "ебату",   # *
                ast.FloorDiv: "ебатская",  # //
                ast.Div: "ебатская",       # /
                ast.Mod: "ебатях",   # %
            }
            op_class = type(node.op)
            if op_class not in op_map:
                raise NotImplementedError(f"Оператор {op_class.__name__} не поддерживается")
            return f"{op_map[op_class]} {left} {right}"

        # Унарные операции
        if isinstance(node, ast.UnaryOp):
            operand = self.transpile_expr(node.operand)
            if isinstance(node.op, ast.Not):
                return f"хуёвый {operand}"
            elif isinstance(node.op, ast.USub):
                return f"ебатям {encode_int(0)} {operand}"

        # Операции сравнения
        if isinstance(node, ast.Compare):
            left = self.transpile_expr(node.left)
            right = self.transpile_expr(node.comparators[0])
            cmp_op = type(node.ops[0])
            if cmp_op == ast.Eq:
                return f"хуем {left} {right}"
            elif cmp_op == ast.NotEq:
                return f"хуёвый хуем {left} {right}"
            elif cmp_op == ast.Lt:
                return f"хуя {left} {right}"
            elif cmp_op == ast.LtE:
                return f"хуёвый хуе {left} {right}"  # not (left > right)
            elif cmp_op == ast.Gt:
                return f"хуе {left} {right}"
            elif cmp_op == ast.GtE:
                return f"хуёвый хуя {left} {right}"  # not (left < right)

        # Логические связки and / or
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                res = self.transpile_expr(node.values[0])
                for v in node.values[1:]:
                    nxt = self.transpile_expr(v)
                    # a and b -> (not (not a)) * (not (not b))
                    res = f"ебату хуёвый хуёвый {res} хуёвый хуёвый {nxt}"
                return res
            elif isinstance(node.op, ast.Or):
                res = self.transpile_expr(node.values[0])
                for v in node.values[1:]:
                    nxt = self.transpile_expr(v)
                    # a or b -> ((a + b) > 0)
                    res = f"хуе ебатей {res} {nxt} {encode_int(0)}"
                return res

        # Вызов функции: ебати <func_id> <arg1> ... <argN> пиздец
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                fname = node.func.id
                func_id = self.symbols.get_func_id(fname)
                arg_exprs = [self.transpile_expr(a) for a in node.args]
                args_str = f" {' '.join(arg_exprs)}" if arg_exprs else ""
                return f"ебати {encode_int(func_id)}{args_str} пиздец"

        raise NotImplementedError(f"Выражение {ast.dump(node)} не поддерживается")

    # =========================================================================
    # СТАТУСЫ И УПРАВЛЯЮЩИЕ КОНСТРУКЦИИ (STATEMENTS)
    # =========================================================================

    def visit_Assign(self, node: ast.Assign):
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            raise NotImplementedError("Присваивание поддерживается только в простые имена")

        var_name = target.id
        var_id = self.symbols.get_var_id(var_name)

        # Декларация переменной при первом упоминании
        if var_name not in self.symbols.declared_vars:
            self.emit(f"блядь {encode_int(var_id)}", f"var {var_name}")
            self.symbols.declared_vars.add(var_name)

        # Особый случай: x = int(input())
        if (isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "int" and node.value.args
                and isinstance(node.value.args[0], ast.Call)
                and isinstance(node.value.args[0].func, ast.Name)
                and node.value.args[0].func.id == "input"):
            self.emit(f"пиздю {encode_int(var_id)}", f"{var_name} = int(input())")
            return

        val_expr = self.transpile_expr(node.value)
        self.emit(f"блядям {encode_int(var_id)} {val_expr}", f"{var_name} = ...")

    def visit_AugAssign(self, node: ast.AugAssign):
        """Десугаризация x += 1 -> x = x + 1."""
        target = node.target
        if not isinstance(target, ast.Name):
            raise NotImplementedError("AugAssign только для имён")
        fake_binop = ast.BinOp(left=target, op=node.op, right=node.value)
        fake_assign = ast.Assign(targets=[target], value=fake_binop)
        self.visit_Assign(fake_assign)

    def visit_Expr(self, node: ast.Expr):
        # Вызов print(...)
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "print":
            for arg in node.value.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    self.emit(f"пиздёж {encode_str(arg.value)}", f'print("{arg.value}")')
                else:
                    expr_code = self.transpile_expr(arg)
                    self.emit(f"пиздеть {expr_code}", "print(...)")
            return

        # Простой вызов функции (с сохранением в фиктивную переменную)
        if isinstance(node.value, ast.Call):
            dummy_id = encode_int(0)
            call_code = self.transpile_expr(node.value)
            self.emit(f"блядям {dummy_id} {call_code}", "discarded call")
            return

        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        cond_str = self.transpile_expr(node.test)
        self.emit(f"хуй {cond_str} пизда", "if condition")
        self.indent_level += 1
        for s in node.body:
            self.visit(s)
        self.indent_level -= 1

        if node.orelse:
            self.emit("пиздец хую пизда", "else")
            self.indent_level += 1
            for s in node.orelse:
                self.visit(s)
            self.indent_level -= 1

        self.emit("пиздец", "end if")

    def visit_While(self, node: ast.While):
        cond_str = self.transpile_expr(node.test)
        self.emit(f"хуёв {cond_str} пизда", "while condition")
        self.indent_level += 1
        for s in node.body:
            self.visit(s)
        self.indent_level -= 1
        self.emit("пиздец", "end while")

    def visit_For(self, node: ast.For):
        """Десугаризация for i in range(...) в while цикл."""
        if not (isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == "range"):
            raise NotImplementedError("Поддерживается только итератор range(...)")
        if not isinstance(node.target, ast.Name):
            raise NotImplementedError("Цель цикла for должна быть простой переменной")

        var_name = node.target.id
        var_id = self.symbols.get_var_id(var_name)
        if var_name not in self.symbols.declared_vars:
            self.emit(f"блядь {encode_int(var_id)}", f"var {var_name}")
            self.symbols.declared_vars.add(var_name)

        args = node.iter.args
        if len(args) == 1:
            start_expr = encode_int(0)
            stop_expr = self.transpile_expr(args[0])
            step_expr = encode_int(1)
        elif len(args) == 2:
            start_expr = self.transpile_expr(args[0])
            stop_expr = self.transpile_expr(args[1])
            step_expr = encode_int(1)
        elif len(args) == 3:
            start_expr = self.transpile_expr(args[0])
            stop_expr = self.transpile_expr(args[1])
            step_expr = self.transpile_expr(args[2])
        else:
            raise NotImplementedError("Некорректная арность range()")

        # Инициализация i = start
        self.emit(f"блядям {encode_int(var_id)} {start_expr}", f"{var_name} = start")

        # Цикл: while i < stop
        cond_str = f"хуя бляди {encode_int(var_id)} {stop_expr}"
        self.emit(f"хуёв {cond_str} пизда", f"for {var_name} in range(...)")
        self.indent_level += 1

        for s in node.body:
            self.visit(s)

        # Инкремент: i = i + step
        self.emit(f"блядям {encode_int(var_id)} ебатей бляди {encode_int(var_id)} {step_expr}", f"{var_name} += step")
        self.indent_level -= 1
        self.emit("пиздец", "end for")

    def visit_Break(self, node: ast.Break):
        self.emit("хуи", "break")

    def visit_Return(self, node: ast.Return):
        if node.value:
            val_str = self.transpile_expr(node.value)
            self.emit(f"ебатями {val_str}", "return expr")
        else:
            self.emit(f"ебатями {encode_int(0)}", "return 0")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        func_id = self.symbols.get_func_id(node.name)
        param_count = len(node.args.args)

        # Сохранение контекста аргументов
        old_args = self.current_scope_args
        self.current_scope_args = {arg.arg: idx for idx, arg in enumerate(node.args.args)}

        self.emit(f"ебать {encode_int(func_id)} {encode_int(param_count)} пизда", f"def {node.name}(...)")
        self.indent_level += 1

        for s in node.body:
            self.visit(s)

        self.indent_level -= 1
        self.emit("пиздец", f"end def {node.name}")
        self.current_scope_args = old_args

    def transpile(self, tree: ast.AST) -> str:
        self.emit("# СКОМПИЛИРОВАНО ИЗ PYTHON 3.11 В BLYADOCODE+")
        self.emit("блядство", "Инициализация модуля")
        for stmt in tree.body:
            self.visit(stmt)
        self.emit("ебатство", "HALT / Конец программы")
        return "\n".join(self.lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Транслятор из базового Python 3.11 в Blyadocode+")
    parser.add_argument("source", help="Исходный файл .py")
    parser.add_argument("-o", "--output", help="Выходной файл .blyad", default=None)
    args = parser.parse_args()

    with open(args.source, "r", encoding="utf-8") as f:
        src = f.read()

    tree = ast.parse(src)
    transpiler = BlyadTranspiler()
    blyad_code = transpiler.transpile(tree)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(blyad_code)
        print(f"[OK] Трансляция успешно завершена в '{args.output}'.")
    else:
        print(blyad_code)

if __name__ == "__main__":
    main()
