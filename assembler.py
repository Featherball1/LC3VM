import argparse
import re
from collections import defaultdict
from enum import Enum
from pprint import pprint
from typing import List, Callable
from dataclasses import dataclass

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

trap_codes = [
    "GETC", "OUT", "PUTS", "IN", "PUTSP", "HALT"
]

preprocessor_directives = [
    ".ORIG", ".END", ".BLKW", ".FILL", ".STRINGZ"
]

asm_keywords = opcodes + trap_codes + preprocessor_directives

class TokenType(Enum):
    LABEL = 'label'
    OPCODE = 'opcode'
    DOT = 'dot'
    CONST = 'const'
    REG = 'reg'
    STR = 'str'

@dataclass
class Token:
    pass

class ErrorCodes(Enum):
    ERR_OPEN_READ = "Could not open file for reading"
    ERR_NO_ORIG = "Could not find .ORIG directive - program entry point not found"
    ERR_UNKNOWN_KEYWORD = "Keyword does not exist"

@dataclass
class Symbol:
    name: str
    addr: int

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

def tokenize_line(line: str) -> List[str]:
    """
    TODO: This currently can't handle spaces in .STRINGZ strings
    Eg HELLOWORLD	.STRINGZ "Hello World\n" in test.asm
    gets tokenized as ["Hello", "World\n",] which is not correct

    For now: delete the whitespace so that we can check the program works, then
    iron out the tokenization details later
    """

    # Convert a single line of LC3 tokens into an iterable of tokens
    # The function
        # Takes as input the source code line
        # Returns the first token of the line or the NULL token
        # Separates tokens by whitespace or commas (returning commas as part of the list)
        # Discards all the LC3 end of line comments, discards empty lines / comment only lines
        # For quoted strings used by the .STRINGZ directive, the returned token preserves opening/closing quote marks 
        # but converts all internal escape sequences into their actual character value

    # Split into non-comment and comment portion
    uncommented_line = line.split(";")[0]
    stripped_whitespace = uncommented_line.split()
    tokens = []
    for substring in stripped_whitespace:
        # The list comprehension hack here is to get around the fact that you'll get a '' element
        # in lists returned from .split("delimiter") in Python
        for token in [x for x in substring.split(",") if x]:
            tokens.append(token.strip())
    return tokens

def match_syntax(line: str) -> bool:
    # Check if the provided line matches LC3 syntax
    # The standard form of LC3 syntax is
        # [label] opcode operands [; optional end of line comment]
    pass

def scan_operands(op_tokens: List[str]):
    pass

class Assembler:
    def __init__(self, filepath: str, debug: bool = True):
        self.filepath = filepath
        self.debug = debug
        self.symbol_table = None
        self.lines_metadata = None
    
    def __enter__(self):
        self.file = open(self.filepath)
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.file.close()

    def encode_operand(self):
        # Will be used in pass 2
        pass

    def encode_PC_offset_or_error(self):
        # Will be used in pass 2
        pass

    def scan(self):
        """
        In the scanning phase of assembling:
            - Tokenize the line
            - Check if an opcode is present
                - Look at the first token. If it is not an opcode, assume it is a label.
            - Based on the opcode/label, write the metadata to a LineInfo dataclass
        """

        # Phase one of assembling
        symbol_table = {}
        lines_metadata = []
        location_counter = 0x0
        for line_idx, line in enumerate(self.file):
            tokens = tokenize_line(line)
            if not tokens: continue
            # TODO: check_syntax(tokens)

            # The .END directive is treated separately from the others
            if tokens[0] == ".END":
                if self.debug: print(f"Line {line_idx} program end point found, exiting scanning")
                lines_metadata.append((tokens, False, hex(location_counter), line_idx))
                break

            instr_idx = 0   # Used for indexing incase there's a label
            label = None    # Will hold the label if there is one
            if tokens[0] not in asm_keywords:
                # There is a label
                instr_idx = 1
                label = tokens[0]

            """CASE 1: We encounter a symbol"""
            if label != None:
                if label in symbol_table.keys(): 
                    print("ERROR: The label {label} on line {line_idx} was already present in the symbol table (already defined)")
                    return

                symbol_table[label] = location_counter
                lines_metadata.append((tokens, True, hex(location_counter), line_idx))
            
            """CASE 2: We encounter a preprocessor directive"""
            if tokens[instr_idx] in preprocessor_directives:
                # TODO: Implement the other preprocessor directives
                if tokens[instr_idx] == ".ORIG":
                    # .ORIG [address]
                    location_counter = int('0' + tokens[1], 16)
                elif tokens[instr_idx] == ".STRINGZ":
                    # [label] .STRINGZ [string]
                    location_counter = location_counter + len(tokens[2]) + 1
                
                lines_metadata.append((tokens, False, hex(location_counter), line_idx))

            """CASE 3: We encounter an opcode"""
            if tokens[instr_idx] in opcodes:
                location_counter = location_counter + 1
                lines_metadata.append((tokens, False, hex(location_counter), line_idx))

            """CASE 4: We encounter a trapcode"""
            if tokens[instr_idx] in trap_codes:
                location_counter = location_counter + 1
                lines_metadata.append((tokens, False, hex(location_counter), line_idx))

            if self.debug:  print(f"""
            LINE PROCESSING RESULTS
            Line {line_idx} split into tokens {tokens}
            There is a label {label}
            The instruction is {tokens[instr_idx]}
            The location counter is {hex(location_counter)}
            ------------------------------------------
            """)

        self.symbol_table = symbol_table
        self.lines_metadata = lines_metadata
        #return symbol_table, lines_metadata
    
    def print_first_pass_results(self):
        print("---------- SUMMARY ----------")
        print("---------- SYMBOL TABLE {{label: address}} -----------")
        pprint(self.symbol_table)
        print("---------- SOURCE LINES (tokens, location_counter, source_file_line) -----------")
        pprint(self.lines_metadata)

    def generate(self):
        # Phase 2 of assembling
        for idx, tup in enumerate(self.lines_metadata):
            tokens, has_label, location_counter, source_line = tup
            if tokens[0] == '.END':
                if self.debug: print(f"Line {source_line} program end point found, exiting generation")
            
            if self.debug: print(tokens)
            
            if not has_label:
                pass

# Set up the user-facing CLI interface
parser = argparse.ArgumentParser()
parser.add_argument("inputs", metavar = "INPUT", nargs = "*", help = "Input files to assemble")
args = parser.parse_args()

for i in args.inputs:
    assembler = Assembler(i)
    with assembler as assemble:
        print("SCANNING")
        assembler.scan()
        assembler.print_first_pass_results()
        print("GENERATING")
        assembler.generate()