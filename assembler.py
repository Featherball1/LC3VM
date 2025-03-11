import argparse
import array
from enum import Enum
from typing import List
from dataclasses import dataclass
import os

"""
The structure of LC3 assembly code

Label:
    - Placed at the beginning of a line
    - Assigns a symbolic name to the address corresponding to the line
Opcode: 
    - reserved symbols corresponding to LC3 instructions
Operands: 
    - Registers - specified by Rn, n being the register number
    - Numbers - indicated by # (decimal), x (hex), b (binary)
    - label - symbolic name of memory location
    - Separated by commas
    - Number, order and type correspond to instruction format
Comment:
    - Anything after a semicolon is a comment, and ignored by the assembler
Assembler directives:
    - Refer to operations used by the assembler, not like the program
    - The opcode for assembler directives begins with a .
Trap codes:
    - 

The LC3 assembly syntax has the form
    [label] opcode operands [; optional end of line comment]
    
Examples:
(Assembler directives)
    .ORIG x3000 ; program starts at address x3000
    .END ; end of program
    ADDR2   .BLKW   1  ; Reserve a memory word
    .FILL 
    .STRINGZ

(Instructions)
    ADD R3, R1, #2  ; Add 2 store into R3
    ST R3, ADDR2    ; Store R3 into whatever ADDR2 is
"""

"""
The first and second passes in assembly

The first pass must
    - Verify syntactic correctness of each line
        - Identify the LC3 operator, check operands are correct in number and type
        - Skip empty lines orcomment lines
        - If the line contains code, determine the address of the next instruction
        - Whenever a line contains a label, insert it and its address into the symbol table
            - Required for computation of PCoffset in second phase

    - Store the above syntactic analysis in a symbol table

The second pass must
    - Generate object code from the .asm file
        - By generating the LC3 words required for each instruction by generating the correct 16-bit patterns that identify the instruction
        - Computing PCoffset for LD/ST/LDI/STI/BR/JSR/LEA, determine if it is range and insert into bit pattern
        - Report out-of-range offsets as errors
"""

opcodes = [
    "ADD", "AND", "NOT", "BR", "JMP", "JSR", "LD", "LDI",
    "LDR", "LEA", "ST", "STI", "STR", "TRAP", "RES", "RTI"
]

opcodes_dict = {
    "ADD" : 0x1,
    "AND" : 0x5,
    "BR" : 0x0,
    "JMP" : 0xC,
    "JSR" : 0x4,
    "LD" : 0X2,
    "LDI" : 0xA,
    "LDR" : 0x6,
    "LEA" : 0xE,
    "NOT" : 0x9,
    "RET" : 0xC,
    "RTI" : 0x8,
    "ST" : 0x3,
    "STI" : 0xB,
    "STR" : 0x7,
    "TRAP" : 0xF
}

trap_codes = [
    "GETC", "OUT", "PUTS", "IN", "PUTSP", "HALT"
]

opcodes_trapcodes = opcodes + trap_codes

trap_codes_dict = {
    "GETC" : 0x20,
    "OUT" : 0x21,
    "PUTS" : 0x22,
    "IN" : 0x23,
    "PUTSP" : 0x24,
    "HALT" : 0x25,
}

preprocessor_directives = [
    ".ORIG", ".END", ".BLKW", ".FILL", ".STRINGZ"
]

registers = [
    "R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7"
]

registers_dict = {
    "R0" : 0x0,
    "R1" : 0x1,
    "R3" : 0X2,
    "R4" : 0x3,
    "R5" : 0x4,
    "R6" : 0x5,
    "R7" : 0x6,
    "R_PC" : 0x7,
    "R_COND" : 0x8,
    "R_COUNT" : 0x9,
}

asm_keywords = opcodes + trap_codes + preprocessor_directives

"""
For the purpose of assembly, we record a bit of metadata on the token while the tokenizer runs.
This is TokenType, categorizing the type of assembly keyword the token corresponds to.
The struct Token thus contains the token value (as a string) and the token type (as a TokenType enum-class)
"""

class TokenType(Enum):
    LABEL = 'label'
    OPCODE = 'opcode'
    ASSEMBLER_DIRECTIVE = 'directive'
    CONST = 'const'
    REGISTER = 'register'
    STRING = 'str'
    TRAP_CODE = 'trap_code'
    NULL_TOKEN = 'null_token'

@dataclass
class Token:
    value: str = None
    token_type: TokenType = None

@dataclass
class LineInfo:
    line_idx: int
    addr: int
    machine_code: int
    opcode: str
    reg1: int
    reg2: int
    reg3: int
    imm: int
    label_ref: str

""" PHASE ONE ASSEMBLY: TOKENISATION AND SCANNING """

def tokenize_line(line: str) -> List[Token]:
    """
    TODO: This currently can't handle spaces in .STRINGZ strings
    Eg HELLOWORLD	.STRINGZ "Hello World\n" in test.asm
    gets tokenized as ["Hello", "World\n",] which is not correct

    For now: delete the whitespace so that we can check the program works, then
    iron out the tokenization details later
    """

    """
    This function converts a single source line into an iterable of tokens
    It takes as input the source code line, and skips it if it is empty or a comment
    It discards EOL comments by splitting according to where the ";" occurs.
    For each token
        - It identifies the token type (possible in the tokenizer because LC3 syntax is very simple)
        - It adds a Token object to the iterable of tokens
    It returns the iterable of tokens
    """

    # Split into non-comment and comment portion
    uncommented_line = line.split(";")[0]
    stripped_whitespace = uncommented_line.split()
    tokens = []
    token_idx = 0
    for substring in stripped_whitespace:
        # The list comprehension hack here is to get around the fact that you'll get a '' element
        # in lists returned from .split("delimiter") in Python
        for token in [x for x in substring.split(",") if x]:
            """CASE 0: Set token type to be the placeholder"""
            token_type = TokenType.NULL_TOKEN

            # Identify the correct token type for the given token
            # Since LC3 syntax is so simple, it's possible to just enumerate cases here

            """CASE 1: We encounter an opcode"""
            if token in opcodes:
                token_type = TokenType.OPCODE
                
                """CASE 2: We have encountered an assembler directive"""
            elif token.startswith("."):
                token_type = TokenType.ASSEMBLER_DIRECTIVE
                
                """CASE 3: We have encountered a register symbol"""
            elif token in registers:
                token_type = TokenType.REGISTER
            
                """CASE 4: We have encountered a trap code"""
            elif token in trap_codes:
                token_type = TokenType.TRAP_CODE
                
                # Note that labels can only appear at the start of a line
                """CASE 5: We have encountered a label"""
            elif token_idx == 0:
                token_type = TokenType.LABEL
            
                """CASE 6: We have encountered a constant"""
            else:
                token_type = TokenType.CONST

            token = Token(token.strip(), token_type)
            
            tokens.append(token)
        token_idx += 1
    return tokens

def scan(filepath: str, debug: bool = True):
    """
    In the scanning phase of assembling:
        - Tokenize the line
        - Check if an opcode is present
            - Look at the first token. If it is not an opcode, assume it is a label.
        - Based on the opcode/label, write the metadata to a LineInfo dataclass
    """

    file = open(filepath)
    symbol_table = {}
    lines_metadata = []
    location_counter = 0x0
    for line_idx, line in enumerate(file):
        tokens = tokenize_line(line)

        """CASE 0: The line was empty"""
        if not tokens: continue

        # TODO: check_syntax(tokens)

        """CASE 1: We encounter the program endpoint"""
        if tokens[0].value == ".END":
            if debug: print(f"Line {line_idx} program end point found, exiting scanning")
            lines_metadata.append((tokens, hex(location_counter)))
            break

        """CASE 2: We encounter a label"""
        if tokens[0].token_type == TokenType.LABEL:
            if tokens[0].value in symbol_table.keys(): 
                print("ERROR: The label {label} on line {line_idx} was already present in the symbol table (already defined)")
                return
            symbol_table[tokens[0].value] = location_counter

        """CASE 3: We encounter a preprocessor directive"""
        # Directives that don't accept a label
        if tokens[0].token_type == TokenType.ASSEMBLER_DIRECTIVE:
            if tokens[0].value == ".ORIG":
                # .ORIG [address]
                location_counter = int('0' + tokens[1].value, 16)
                print("FOUND PROGRAM ENTRY POINT, SETTING LOCATION COUNTER TO", location_counter)
        # .STRINGZ is a special case, because it takes a label
        elif len(tokens) > 1 and tokens[1].token_type == TokenType.ASSEMBLER_DIRECTIVE:
            if tokens[1].value == ".STRINGZ":
                # [label] .STRINGZ [string]
                symbol_table[tokens[0].value] = location_counter
                location_counter = location_counter + len(tokens[2].value) + 1

        """CASE 4: We encounter an opcode"""
        if tokens[0].token_type == TokenType.OPCODE:
            location_counter = location_counter + 1

        """CASE 5: We encounter a trapcode"""
        if tokens[0].token_type == TokenType.TRAP_CODE:
            location_counter = location_counter + 1

        if debug:  print(f"""
LINE PROCESSING RESULTS
Line {line_idx} split into tokens {tokens}
The location counter is {location_counter}, {hex(location_counter)}
------------------------------------------
        """)
            
        lines_metadata.append((tokens, hex(location_counter)))

    file.close()

    return symbol_table, lines_metadata

"""PHASE TWO ASSEMBLY: ENCODINGS AND GENERATION"""

"""
; Basic lc3 program.

; Semi-colons are used to create comments.

			.ORIG x3000

			LEA R0, HELLOWORLD
			PUTS
			HALT
	
HELLOWORLD	.STRINGZ "HelloWorld\n"

			.END
"""

def encode_add(opcode, symbol_table, location_counter, tokens):
    pass


def encode_and(opcode, symbol_table, location_counter, tokens):
    pass

def encode_not(opcode, symbol_table, location_counter, tokens):
    return opcodes_dict[opcode] | registers_dict[tokens[1].value] << 9 | registers_dict[tokens[2].value] << 6 | 0b11111

def encode_br(opcode, symbol_table, location_counter, tokens):
    #return opcodes_dict[opcode] | 
    pass

def encode_jmp(opcode, symbol_table, location_counter, tokens):
    return opcodes_dict[opcode] | 0b000 << 9 | registers_dict[tokens[1].value] << 6 | 0b000000

def encode_jsr(opcode, symbol_table, location_counter, tokens):
    return opcodes_dict[opcode] | 1 << 11 | (symbol_table[tokens[1].value] - location_counter) & 0b11111111111

def encode_add(opcode, symbol_table, location_counter, tokens):
    pass

def encode_ld(opcode, symbol_table, location_counter, tokens):
    pass

def encode_ldi(opcode, symbol_table, location_counter, tokens):
    pass

def encode_ldr(opcode, symbol_table, location_counter, tokens):
    pass

def encode_lea(opcode, symbol_table, location_counter, tokens):
    print(f"LEA ENCODING: {opcodes_dict[opcode] << 12 | registers_dict[tokens[1].value] << 9 | (symbol_table[tokens[2].value] - int(location_counter, 16)) & 0b11111111}")
    print(f"""
opcode: {opcodes_dict[opcode] << 12}
dr: {registers_dict[tokens[1].value]}
last bit: { (symbol_table[tokens[2].value] - int(location_counter, 16)) & 0b11111111}
""")
    return opcodes_dict[opcode] << 12 | registers_dict[tokens[1].value] << 9 | (symbol_table[tokens[2].value] - int(location_counter, 16)) & 0b11111111

def encode_st(opcode, symbol_table, location_counter, tokens):
    pass

def encode_sti(opcode, symbol_table, location_counter, tokens):
    pass

def encode_str(opcode, symbol_table, location_counter, tokens):
    pass

def encode_trap(opcode, symbol_table, location_counter, tokens):
    return opcodes_dict["TRAP"] << 12 | trap_codes_dict[tokens[0].value]

def encode_res(opcode, symbol_table, location_counter, tokens):
    pass

def encode_rti(opcode, symbol_table, location_counter, tokens):
    return 0b1000000000000000

encodings = {
    'ADD' : lambda opcode, symbol_table, location_counter, tokens: encode_add(opcode, symbol_table, location_counter, tokens),
    'AND' : lambda opcode, symbol_table, location_counter, tokens: encode_and(opcode, symbol_table, location_counter, tokens),
    'NOT' : lambda opcode, symbol_table, location_counter, tokens: encode_not(opcode, symbol_table, location_counter, tokens),
    'BR' : lambda opcode, symbol_table, location_counter, tokens: encode_br(opcode, symbol_table, location_counter, tokens),
    'JMP' : lambda opcode, symbol_table, location_counter, tokens: encode_jmp(opcode, symbol_table, location_counter, tokens),
    'JSR' : lambda opcode, symbol_table, location_counter, tokens: encode_jsr(opcode, symbol_table, location_counter, tokens),
    'LD' : lambda opcode, symbol_table, location_counter, tokens: encode_ld(opcode, symbol_table, location_counter, tokens),
    'LDI' : lambda opcode, symbol_table, location_counter, tokens: encode_ldi(opcode, symbol_table, location_counter, tokens),
    'LDR' : lambda opcode, symbol_table, location_counter, tokens: encode_ldr(opcode, symbol_table, location_counter, tokens),
    'LEA' : lambda opcode, symbol_table, location_counter, tokens: encode_lea(opcode, symbol_table, location_counter, tokens),
    'ST' : lambda opcode, symbol_table, location_counter, tokens: encode_st(opcode, symbol_table, location_counter, tokens),
    'STI' : lambda opcode, symbol_table, location_counter, tokens: encode_sti(opcode, symbol_table, location_counter, tokens),
    'STR' : lambda opcode, symbol_table, location_counter, tokens: encode_str(opcode, symbol_table, location_counter, tokens),
    'TRAP' : lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
    'RES' : lambda opcode, symbol_table, location_counter, tokens: encode_res(opcode, symbol_table, location_counter, tokens),
    'RTI' : lambda opcode, symbol_table, location_counter, tokens: encode_rti(opcode, symbol_table, location_counter, tokens),

    'GETC': lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
    'OUT': lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
    'PUTS': lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
    'IN': lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
    'PUTSP': lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
    'HALT': lambda opcode, symbol_table, location_counter, tokens: encode_trap(opcode, symbol_table, location_counter, tokens),
}

def generate(symbol_table, lines_metadata, filepath: str, debug: bool = True):
    # Phase 2 of assembling
    CONDS = {
        '.STRINGZ': lambda tokens, data, sym, lc:
        data.fromlist([c for c in tokens[1].value.encode()]) or data.append(0x0),

        **{
            op: lambda toks, data, sym, lc:
            data.append(encodings[toks[0].value](toks[0].value, sym, lc, toks))
            for op  in opcodes_trapcodes
        }
    }

    data = array.array("H", [])
    data.append(int('0' + lines_metadata[0][0][1].value, 16))

    for tokens, lc in lines_metadata[1:]:

        print("LINE:", tokens, lc)
        if tokens[0].value == '.END':
            break
        print(tokens)

        if tokens[0].token_type != TokenType.LABEL:
            CONDS[tokens[0].value](tokens, data, symbol_table, lc)
        elif len(tokens) != 1:
            CONDS[tokens[1].value](tokens[1:], data, symbol_table, lc)

    data.byteswap()
    return data

# Set up the user-facing CLI interface
parser = argparse.ArgumentParser()
parser.add_argument("inputs", metavar = "INPUT", nargs = "*", help = "Input files to assemble")
args = parser.parse_args()

for i in args.inputs:
    print("SCANNING")
    symbol_table, lines_metadata = scan(i)
    #assembler.print_first_pass_results()
    print("GENERATING")
    data = generate(symbol_table, lines_metadata, i)
    print("GENERATION RESULTS")
    print(data.tobytes().hex())

    file_name = os.path.splitext(i)[0]
    file_name = f'{file_name}-assembled.obj'

    with open(file_name, 'wb') as f:
        f.write(data.tobytes())
    
    print("Saved", file_name)