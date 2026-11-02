#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ЭТАЛОННЫЙ КОМПИЛЯТОР И РАНТАЙМ ЯЗЫКА ПРОГРАММИРОВАНИЯ BLYADOCODE+
Соответствие стандарту: ISO/IEC JTC1/SC22/BLYAD-PLUS-STD-2026 (v2.0.0-PROPOSAL)
"""

import sys
import argparse
from typing import List, Any, Dict, Optional, Tuple

# =====================================================================
# 1. АЛГЕБРАИЧЕСКИЙ БАЗИС И КАНОНИЧЕСКАЯ МАТРИЦА M_{4x9}
# =====================================================================

CANONICAL_MATRIX = {
    # R0: Statica (Данные, состояние)
    "блядь":    ("R0", 0, "NOM"),  # Определение / Базис
    "бляди":    ("R0", 1, "GEN"),  # Разыменование / R-value
    "блядью":   ("R0", 2, "DAT"),  # Аргумент-приёмник
    "блядей":   ("R0", 3, "ACC"),  # Аккумулятор / Цель
    "блядям":   ("R0", 4, "INS"),  # Мутация / Присваивание
    "блядями":  ("R0", 5, "ABL"),  # Деаллокация / Drop
    "блядях":   ("R0", 6, "LOC"),  # Локальный скоуп
    "блядская": ("R0", 7, "PRD"),  # Проверка типа
    "блядство": ("R0", 8, "TER"),  # Точка входа / Модуль

    # R1: Negatio (Логика, инварианты, ветвление)
    "хуй":      ("R1", 0, "NOM"),  # Ветвление IF
    "хуя":      ("R1", 1, "GEN"),  # Меньше (<)
    "хую":      ("R1", 2, "DAT"),  # Ветка ELSE
    "хуем":     ("R1", 3, "ACC"),  # Равно (==)
    "хуе":      ("R1", 4, "INS"),  # Больше (>)
    "хуи":      ("R1", 5, "ABL"),  # Прерывание цикла (BREAK)
    "хуёв":     ("R1", 6, "LOC"),  # Цикл WHILE
    "хуёвый":   ("R1", 7, "PRD"),  # Логическое НЕ / IsZero
    "хуёвина":  ("R1", 8, "TER"),  # Системный Assert / Panic

    # R2: Spatium (Топология памяти, скоупы, коллекции, I/O)
    "пизда":    ("R2", 0, "NOM"),  # Начало блока {
    "пизды":    ("R2", 1, "GEN"),  # Индексация коллекции
    "пизде":    ("R2", 2, "DAT"),  # Запись в коллекцию
    "пизду":    ("R2", 3, "ACC"),  # Чтение из коллекции
    "пиздой":   ("R2", 4, "INS"),  # Открывающая кавычка квотирования ⟪
    "пиздец":   ("R2", 5, "ABL"),  # Конец блока } / Закрывающая кавычка ⟫
    "пиздеть":  ("R2", 6, "LOC"),  # Вывод числа в STDOUT
    "пиздёж":   ("R2", 7, "PRD"),  # Вывод строки в STDOUT
    "пиздю":    ("R2", 8, "TER"),  # Ввод из STDIN

    # R3: Actio (Морфизмы, вычисления, редукция)
    "ебать":    ("R3", 0, "NOM"),  # Объявление функции
    "ебати":    ("R3", 1, "GEN"),  # Вызов функции
    "ебату":    ("R3", 2, "DAT"),  # Умножение (*)
    "ебатей":   ("R3", 3, "ACC"),  # Сложение (+)
    "ебатям":   ("R3", 4, "INS"),  # Вычитание (-)
    "ебатями":  ("R3", 5, "ABL"),  # Возврат значения (RETURN)
    "ебатях":   ("R3", 6, "LOC"),  # Остаток от деления (%)
    "ебатская": ("R3", 7, "PRD"),  # Целочисленное деление (//)
    "ебатство": ("R3", 8, "TER"),  # Системный HALT / Exit
}

# Четверичный базис B4 <-> {0, 1, 2, 3}
B4_DIGITS = {
    "блядь": 0,
    "хуй": 1,
    "пизда": 2,
    "ебать": 3
}
B4_REV = {v: k for k, v in B4_DIGITS.items()}


# =====================================================================
# 2. ИСКЛЮЧЕНИЯ И СИСТЕМНЫЕ ОШИБКИ
# =====================================================================

class BlyadError(Exception):
    def __init__(self, code: str, msg: str, line: int = 0, col: int = 0):
        self.code = code
        self.msg = msg
        self.line = line
        self.col = col
        super().__init__(f"\n[FATAL ERROR {self.code}] (Строка {line}, Позиция {col}): {self.msg}")


# =====================================================================
# 3. ЛЕКСИЧЕСКИЙ АНАЛИЗАТОР (МОРФОЛОГИЧЕСКИЙ ВЕКТОРИЗАТОР)
# =====================================================================

class Token:
    def __init__(self, value: str, kind: str, line: int, col: int, payload: Any = None):
        self.value = value
        self.kind = kind
        self.line = line
        self.col = col
        self.payload = payload

    def __repr__(self):
        return f"Token({self.value}, kind={self.kind}, line={self.line}, col={self.col})"

def normalize_cyrillic(text: str) -> str:
    # Нормализация ё/е для надежности лексического разбора
    return text.replace('ё', 'е').replace('Ё', 'Е').lower()

def lex(source: str) -> List[Token]:
    tokens = []
    lines = source.splitlines()

    for line_idx, line in enumerate(lines, start=1):
        # Удаление однострочных комментариев согласно п. 1.3
        cleaned_line = ""
        i = 0
        while i < len(line):
            if line[i:i+2] == "//" or line[i:i+1] == "#":
                break
            cleaned_line += line[i]
            i += 1

        col = 1
        words_with_pos = []
        for part in cleaned_line.split():
            start_pos = cleaned_line.find(part, col - 1) + 1
            words_with_pos.append((part, start_pos))
            col = start_pos + len(part)

        for word, w_col in words_with_pos:
            norm_word = word.lower()
            # Проверка каноничности
            canonical_match = None
            for canon in CANONICAL_MATRIX:
                if normalize_cyrillic(canon) == normalize_cyrillic(norm_word):
                    canonical_match = canon
                    break

            if canonical_match is None:
                # Инвариант: Любая последовательность w ∉ M вызывает E001
                raise BlyadError("E001: БЛЯДЬ НЕ РАСПОЗНАНА", f"Недопустимая словоформа '{word}'", line_idx, w_col)

            root, case, tag = CANONICAL_MATRIX[canonical_match]
            tokens.append(Token(canonical_match, tag, line_idx, w_col))

    return tokens


# =====================================================================
# 4. ДЕКОДИРОВАНИЕ ЧЕТВЕРИЧНОГО ПОЛИНОМА И КВОТИРОВАНИЯ (B4)
# =====================================================================

def decode_b4_number(digit_tokens: List[Token]) -> int:
    """Полиномиальное декодирование: V = sum(d_i * 4^(N-1-i))"""
    val = 0
    for tok in digit_tokens:
        if tok.value not in B4_DIGITS:
            raise BlyadError("E002: ХУЁВЫЙ ЛИТЕРАЛ", f"Слово '{tok.value}' не принадлежит базису B4", tok.line, tok.col)
        val = val * 4 + B4_DIGITS[tok.value]
    return val

def decode_b4_bytes(digit_tokens: List[Token]) -> str:
    """Побайтовое декодирование (каждый байт кодируется 4 четверичными разрядами)."""
    if len(digit_tokens) % 4 != 0:
        # Если разрядов не кратно 4, декодируем как числовое значение
        return str(decode_b4_number(digit_tokens))
    
    raw_bytes = bytearray()
    for chunk_idx in range(0, len(digit_tokens), 4):
        chunk = digit_tokens[chunk_idx:chunk_idx+4]
        b = 0
        for tok in chunk:
            if tok.value not in B4_DIGITS:
                raise BlyadError("E002: ХУЁВЫЙ ЛИТЕРАЛ", f"Слово '{tok.value}' не принадлежит базису B4", tok.line, tok.col)
            b = b * 4 + B4_DIGITS[tok.value]
        raw_bytes.append(b)
    
    try:
        return raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return raw_bytes.decode('latin-1')

def encode_number_to_b4(val: int) -> List[str]:
    """Кодирование целого числа в канонический вид пиздой ... пиздец."""
    if val == 0:
        return ["пиздой", "блядь", "пиздец"]
    digits = []
    v = abs(val)
    while v > 0:
        digits.append(v % 4)
        v //= 4
    digits.reverse()
    res = ["пиздой"] + [B4_REV[d] for d in digits] + ["пиздец"]
    return res

def encode_string_to_b4(text: str) -> List[str]:
    """Кодирование UTF-8 строки в последовательность B4."""
    raw = text.encode('utf-8')
    tokens = ["пиздой"]
    for b in raw:
        d0 = (b >> 6) & 3
        d1 = (b >> 4) & 3
        d2 = (b >> 2) & 3
        d3 = b & 3
        tokens.extend([B4_REV[d0], B4_REV[d1], B4_REV[d2], B4_REV[d3]])
    tokens.append("пиздец")
    return tokens


# =====================================================================
# 5. СИНТАКСИЧЕСКИЙ АНАЛИЗАТОР (AST)
# =====================================================================

class ASTNode: pass

class NumLiteral(ASTNode):
    def __init__(self, val: int): self.val = val

class StringLiteral(ASTNode):
    def __init__(self, val: str): self.val = val

class VarRef(ASTNode):
    def __init__(self, var_id: int): self.var_id = var_id

class ArgRef(ASTNode):
    def __init__(self, arg_idx: int): self.arg_idx = arg_idx

class BinOp(ASTNode):
    def __init__(self, op: str, left: ASTNode, right: ASTNode):
        self.op = op
        self.left = left
        self.right = right

class UnaryOp(ASTNode):
    def __init__(self, op: str, expr: ASTNode):
        self.op = op
        self.expr = expr

class CallExpr(ASTNode):
    def __init__(self, func_id: int, args: List[ASTNode]):
        self.func_id = func_id
        self.args = args

class VarDecl(ASTNode):
    def __init__(self, var_id: int): self.var_id = var_id

class VarAssign(ASTNode):
    def __init__(self, var_id: int, expr: ASTNode):
        self.var_id = var_id
        self.expr = expr

class PrintInt(ASTNode):
    def __init__(self, expr: ASTNode): self.expr = expr

class PrintStr(ASTNode):
    def __init__(self, text: str): self.text = text

class ReadInput(ASTNode):
    def __init__(self, var_id: int): self.var_id = var_id

class IfStmt(ASTNode):
    def __init__(self, cond: ASTNode, then_body: List[ASTNode], else_body: Optional[List[ASTNode]] = None):
        self.cond = cond
        self.then_body = then_body
        self.else_body = else_body

class WhileStmt(ASTNode):
    def __init__(self, cond: ASTNode, body: List[ASTNode]):
        self.cond = cond
        self.body = body

class BreakStmt(ASTNode): pass

class ReturnStmt(ASTNode):
    def __init__(self, expr: ASTNode): self.expr = expr

class FuncDef(ASTNode):
    def __init__(self, func_id: int, param_count: int, body: List[ASTNode]):
        self.func_id = func_id
        self.param_count = param_count
        self.body = body

class HaltStmt(ASTNode): pass

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_val: Optional[str] = None) -> Token:
        tok = self.peek()
        if not tok:
            raise BlyadError("E002: ХУЁВЫЙ СИНТАКСИС", "Неожиданный конец программы")
        if expected_val and tok.value != expected_val:
            raise BlyadError("E002: ХУЁВЫЙ СИНТАКСИС", f"Ожидалось '{expected_val}', получено '{tok.value}'", tok.line, tok.col)
        self.pos += 1
        return tok

    def parse_literal(self) -> Tuple[int, str]:
        """Разбор изоморфизма квотирования: пиздой ∘ Payload ∘ пиздец"""
        start_tok = self.consume("пиздой")
        digits = []
        while True:
            tok = self.peek()
            if not tok:
                raise BlyadError("E003: ПИЗДЕЦ НЕ НАСТУПИЛ", "Незакрытый скоуп квотирования", start_tok.line, start_tok.col)
            if tok.value == "пиздец":
                self.consume("пиздец")
                break
            digits.append(self.consume())

        num_val = decode_b4_number(digits)
        str_val = decode_b4_bytes(digits)
        return num_val, str_val

    def parse_expression(self) -> ASTNode:
        tok = self.peek()
        if not tok:
            raise BlyadError("E002: ХУЁВЫЙ СИНТАКСИС", "Ожидалось выражение")

        # Литерал
        if tok.value == "пиздой":
            num_val, _ = self.parse_literal()
            return NumLiteral(num_val)

        # Чтение переменной (бляди <id>)
        if tok.value == "бляди":
            self.consume("бляди")
            var_id, _ = self.parse_literal()
            return VarRef(var_id)

        # Чтение аргумента функции (блядью <index>)
        if tok.value == "блядью":
            self.consume("блядью")
            arg_idx, _ = self.parse_literal()
            return ArgRef(arg_idx)

        # Унарная операция отрицания (хуёвый <expr>)
        if tok.value == "хуёвый":
            self.consume("хуёвый")
            expr = self.parse_expression()
            return UnaryOp("NOT", expr)

        # Бинарные арифметические операции (Prefix)
        bin_ops = {
            "ебатей": "+",
            "ебатям": "-",
            "ебату": "*",
            "ебатская": "//",
            "ебатях": "%",
            "хуем": "==",
            "хуя": "<",
            "хуе": ">",
        }
        if tok.value in bin_ops:
            op_tok = self.consume()
            left = self.parse_expression()
            right = self.parse_expression()
            return BinOp(bin_ops[op_tok.value], left, right)

        # Вызов функции: ебати <func_id> <arg1> ... пиздец
        if tok.value == "ебати":
            self.consume("ебати")
            func_id, _ = self.parse_literal()
            args = []
            while self.peek() and self.peek().value != "пиздец":
                args.append(self.parse_expression())
            self.consume("пиздец")
            return CallExpr(func_id, args)

        raise BlyadError("E002: ХУЁВЫЙ СИНТАКСИС", f"Недопустимое начало выражения: '{tok.value}'", tok.line, tok.col)

    def parse_statement(self) -> Optional[ASTNode]:
        tok = self.peek()
        if not tok:
            return None

        # Объявление переменной: блядь <id>
        if tok.value == "блядь":
            self.consume("блядь")
            var_id, _ = self.parse_literal()
            return VarDecl(var_id)

        # Присваивание: блядям <id> <expr>
        if tok.value == "блядям":
            self.consume("блядям")
            var_id, _ = self.parse_literal()
            expr = self.parse_expression()
            return VarAssign(var_id, expr)

        # Вывод целого числа: пиздеть <expr>
        if tok.value == "пиздеть":
            self.consume("пиздеть")
            expr = self.parse_expression()
            return PrintInt(expr)

        # Вывод строкового литерала: пиздёж <literal>
        if tok.value == "пиздёж":
            self.consume("пиздёж")
            _, text = self.parse_literal()
            return PrintStr(text)

        # Ввод целого числа: пиздю <id>
        if tok.value == "пиздю":
            self.consume("пиздю")
            var_id, _ = self.parse_literal()
            return ReadInput(var_id)

        # Ветвление: хуй <cond> пизда <then> пиздец [хую пизда <else> пиздец]
        if tok.value == "хуй":
            self.consume("хуй")
            cond = self.parse_expression()
            self.consume("пизда")
            then_body = self.parse_block()
            else_body = None
            if self.peek() and self.peek().value == "хую":
                self.consume("хую")
                self.consume("пизда")
                else_body = self.parse_block()
            return IfStmt(cond, then_body, else_body)

        # Цикл: хуёв <cond> пизда <body> пиздец
        if tok.value == "хуёв":
            self.consume("хуёв")
            cond = self.parse_expression()
            self.consume("пизда")
            body = self.parse_block()
            return WhileStmt(cond, body)

        # Прерывание цикла: хуи
        if tok.value == "хуи":
            self.consume("хуи")
            return BreakStmt()

        # Возврат значения: ебатями <expr>
        if tok.value == "ебатями":
            self.consume("ебатями")
            expr = self.parse_expression()
            return ReturnStmt(expr)

        # Определение функции: ебать <func_id> <param_count> пизда <body> пиздец
        if tok.value == "ебать":
            self.consume("ебать")
            func_id, _ = self.parse_literal()
            p_count, _ = self.parse_literal()
            self.consume("пизда")
            body = self.parse_block()
            return FuncDef(func_id, p_count, body)

        # Завершение программы: ебатство
        if tok.value == "ебатство":
            self.consume("ебатство")
            return HaltStmt()

        # Мета-состояние модуля: блядство (пропускаем как разделитель секции)
        if tok.value == "блядство":
            self.consume("блядство")
            return None

        raise BlyadError("E002: ХУЁВЫЙ СИНТАКСИС", f"Неожиданная инструкция '{tok.value}'", tok.line, tok.col)

    def parse_block(self) -> List[ASTNode]:
        stmts = []
        while True:
            tok = self.peek()
            if not tok:
                raise BlyadError("E003: ПИЗДЕЦ НЕ НАСТУПИЛ", "Ожидался 'пиздец' для закрытия блока")
            if tok.value == "пиздец":
                self.consume("пиздец")
                break
            s = self.parse_statement()
            if s: stmts.append(s)
        return stmts

    def parse_all(self) -> List[ASTNode]:
        stmts = []
        while self.peek():
            s = self.parse_statement()
            if s: stmts.append(s)
        return stmts


# =====================================================================
# 6. ТРАНСЛЯТОР В PYTHON (AOT COMPILER)
# =====================================================================

class PythonCompiler:
    def __init__(self):
        self.indent_level = 0
        self.lines = [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            "# Сгенерировано эталонным компилятором BLYADOCODE+",
            "import sys",
            "",
            "_mem = {}",
            "_funcs = {}",
            ""
        ]

    def indent(self) -> str:
        return "    " * self.indent_level

    def compile_expr(self, node: ASTNode) -> str:
        if isinstance(node, NumLiteral):
            return str(node.val)
        if isinstance(node, VarRef):
            return f"_mem.get({node.var_id}, 0)"
        if isinstance(node, ArgRef):
            return f"_args[{node.arg_idx}]"
        if isinstance(node, UnaryOp):
            return f"(1 if ({self.compile_expr(node.expr)}) == 0 else 0)"
        if isinstance(node, BinOp):
            l = self.compile_expr(node.left)
            r = self.compile_expr(node.right)
            if node.op == "//":
                return f"({l} // {r} if {r} != 0 else sys.exit('[E005: ПОЛНЫЙ ПИЗДЕЦ] Деление на ноль'))"
            if node.op in ("==", "<", ">"):
                return f"(1 if ({l} {node.op} {r}) else 0)"
            return f"({l} {node.op} {r})"
        if isinstance(node, CallExpr):
            arg_strs = ", ".join(self.compile_expr(a) for a in node.args)
            return f"_funcs[{node.func_id}]([{arg_strs}])"
        raise RuntimeError(f"Unknown expr node: {node}")

    def compile_stmt(self, node: ASTNode):
        if isinstance(node, VarDecl):
            self.lines.append(f"{self.indent()}_mem[{node.var_id}] = 0")
        elif isinstance(node, VarAssign):
            e = self.compile_expr(node.expr)
            self.lines.append(f"{self.indent()}_mem[{node.var_id}] = {e}")
        elif isinstance(node, PrintInt):
            e = self.compile_expr(node.expr)
            self.lines.append(f"{self.indent()}print({e})")
        elif isinstance(node, PrintStr):
            safe_text = repr(node.text)
            self.lines.append(f"{self.indent()}sys.stdout.write({safe_text} + '\\n')")
        elif isinstance(node, ReadInput):
            self.lines.append(f"{self.indent()}_mem[{node.var_id}] = int(sys.stdin.readline().strip())")
        elif isinstance(node, ReturnStmt):
            e = self.compile_expr(node.expr)
            self.lines.append(f"{self.indent()}return {e}")
        elif isinstance(node, BreakStmt):
            self.lines.append(f"{self.indent()}break")
        elif isinstance(node, HaltStmt):
            self.lines.append(f"{self.indent()}sys.exit(0)")
        elif isinstance(node, IfStmt):
            cond_str = self.compile_expr(node.cond)
            self.lines.append(f"{self.indent()}if ({cond_str}) != 0:")
            self.indent_level += 1
            for s in node.then_body: self.compile_stmt(s)
            if not node.then_body: self.lines.append(f"{self.indent()}pass")
            self.indent_level -= 1
            if node.else_body is not None:
                self.lines.append(f"{self.indent()}else:")
                self.indent_level += 1
                for s in node.else_body: self.compile_stmt(s)
                if not node.else_body: self.lines.append(f"{self.indent()}pass")
                self.indent_level -= 1
        elif isinstance(node, WhileStmt):
            cond_str = self.compile_expr(node.cond)
            self.lines.append(f"{self.indent()}while ({cond_str}) != 0:")
            self.indent_level += 1
            for s in node.body: self.compile_stmt(s)
            if not node.body: self.lines.append(f"{self.indent()}pass")
            self.indent_level -= 1
        elif isinstance(node, FuncDef):
            func_name = f"_user_func_{node.func_id}"
            self.lines.append(f"{self.indent()}def {func_name}(_args):")
            self.indent_level += 1
            for s in node.body: self.compile_stmt(s)
            self.lines.append(f"{self.indent()}return 0")
            self.indent_level -= 1
            self.lines.append(f"{self.indent()}_funcs[{node.func_id}] = {func_name}")

    def compile(self, ast: List[ASTNode]) -> str:
        for stmt in ast:
            self.compile_stmt(stmt)
        return "\n".join(self.lines) + "\n"


# =====================================================================
# 7. ВИРТУАЛЬНАЯ МАШИНА / ИНТЕРПРЕТАТОР ПРЯМОГО ВЫЧИСЛЕНИЯ
# =====================================================================

class VMReturn(Exception):
    def __init__(self, val: int): self.val = val

class VMBreak(Exception): pass

class Interpreter:
    def __init__(self):
        self.globals: Dict[int, int] = {}
        self.functions: Dict[int, FuncDef] = {}

    def eval_expr(self, node: ASTNode, args: List[int]) -> int:
        if isinstance(node, NumLiteral):
            return node.val
        if isinstance(node, VarRef):
            return self.globals.get(node.var_id, 0)
        if isinstance(node, ArgRef):
            return args[node.arg_idx] if node.arg_idx < len(args) else 0
        if isinstance(node, UnaryOp):
            return 1 if self.eval_expr(node.expr, args) == 0 else 0
        if isinstance(node, BinOp):
            l = self.eval_expr(node.left, args)
            r = self.eval_expr(node.right, args)
            if node.op == "+": return l + r
            if node.op == "-": return l - r
            if node.op == "*": return l * r
            if node.op == "//":
                if r == 0:
                    raise BlyadError("E005: ПОЛНЫЙ ПИЗДЕЦ", "Деление на ноль в Actio")
                return l // r
            if node.op == "%":
                if r == 0:
                    raise BlyadError("E005: ПОЛНЫЙ ПИЗДЕЦ", "Деление на ноль в Actio")
                return l % r
            if node.op == "==": return 1 if l == r else 0
            if node.op == "<":  return 1 if l < r else 0
            if node.op == ">":  return 1 if l > r else 0
        if isinstance(node, CallExpr):
            if node.func_id not in self.functions:
                raise BlyadError("E004: ЕБАТЬ НЕЛЬЗЯ", f"Функция {node.func_id} не объявлена")
            fdef = self.functions[node.func_id]
            evaled_args = [self.eval_expr(a, args) for a in node.args]
            try:
                for s in fdef.body:
                    self.exec_stmt(s, evaled_args)
            except VMReturn as ret:
                return ret.val
            return 0
        return 0

    def exec_stmt(self, node: ASTNode, args: List[int]):
        if isinstance(node, VarDecl):
            self.globals[node.var_id] = 0
        elif isinstance(node, VarAssign):
            self.globals[node.var_id] = self.eval_expr(node.expr, args)
        elif isinstance(node, PrintInt):
            val = self.eval_expr(node.expr, args)
            print(val)
        elif isinstance(node, PrintStr):
            print(node.text)
        elif isinstance(node, ReadInput):
            try:
                self.globals[node.var_id] = int(input().strip())
            except ValueError:
                self.globals[node.var_id] = 0
        elif isinstance(node, ReturnStmt):
            val = self.eval_expr(node.expr, args)
            raise VMReturn(val)
        elif isinstance(node, BreakStmt):
            raise VMBreak()
        elif isinstance(node, HaltStmt):
            sys.exit(0)
        elif isinstance(node, FuncDef):
            self.functions[node.func_id] = node
        elif isinstance(node, IfStmt):
            cond_val = self.eval_expr(node.cond, args)
            if cond_val != 0:
                for s in node.then_body:
                    self.exec_stmt(s, args)
            elif node.else_body:
                for s in node.else_body:
                    self.exec_stmt(s, args)
        elif isinstance(node, WhileStmt):
            while self.eval_expr(node.cond, args) != 0:
                try:
                    for s in node.body:
                        self.exec_stmt(s, args)
                except VMBreak:
                    break

    def run(self, ast: List[ASTNode]):
        for stmt in ast:
            self.exec_stmt(stmt, [])


# =====================================================================
# 8. CLI И ТОЧКА ВХОДА
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Эталонный компилятор Blyadocode+ (ISO/IEC JTC1/SC22/BLYAD-PLUS-STD-2026)"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Команда run
    run_parser = subparsers.add_parser("run", help="Интерпретировать Blyadocode+ файл")
    run_parser.add_argument("file", help="Путь к исходному коду")

    # Команда compile
    comp_parser = subparsers.add_parser("compile", help="Скомпилировать в исполняемый Python")
    comp_parser.add_argument("file", help="Путь к исходному коду")
    comp_parser.add_argument("-o", "--output", help="Выходной файл (.py)", default="output.py")

    # Кодировщики литералов
    enc_str_p = subparsers.add_parser("encode-str", help="Закодировать строку в четверичный базис")
    enc_str_p.add_argument("text", help="Текст для кодирования")

    enc_int_p = subparsers.add_parser("encode-int", help="Закодировать целое число в четверичный базис")
    enc_int_p.add_argument("number", type=int, help="Число")

    args = parser.parse_args()

    if args.command == "encode-str":
        toks = encode_string_to_b4(args.text)
        print(" ".join(toks))
        return

    if args.command == "encode-int":
        toks = encode_number_to_b4(args.number)
        print(" ".join(toks))
        return

    if args.command in ("run", "compile"):
        with open(args.file, "r", encoding="utf-8") as f:
            src = f.read()

        tokens = lex(src)
        p = Parser(tokens)
        ast = p.parse_all()

        if args.command == "run":
            vm = Interpreter()
            vm.run(ast)
        elif args.command == "compile":
            comp = PythonCompiler()
            out_code = comp.compile(ast)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out_code)
            print(f"[OK] Компиляция завершена: {args.output}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
