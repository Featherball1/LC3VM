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
    "TRAP_GETC", "TRAP_OUT", "TRAP_PUTS", "TRAP_IN", "TRAP_PUTSP",
    "TRAP_HALT"
]

preprocessor_directives = [
    ".ORIG", ".END", ".BLKW", ".FILL", ".STRINGZ"
]

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

class SymbolTable:
    def __init__(self):
        self.symbol_table = defaultdict()

    def symbol_init(self, lookup_by_addr: int):
        self.symbol_table[lookup_by_addr] = "name"

    def clear(self):
        # Remove all symbols from the table (reset)
        self.symbol_table = defaultdict()

    def search(self, name: str) -> Symbol:
        # Find a symbol by its name
        return {f"{name}" : self.symbol_table[name]}

    def search(self, addr: int) -> Symbol:
        # Find a symbol by its address
        pass

    def map(self, f: Callable):
        # Apply f to all entries in the symbol table
        pass

def tokenize_line(line: str) -> List[str]:
    # Convert a single line of LC3 tokens into an iterable of tokens
    # The function
        # Takes as input the source code line
        # Returns the first token of the line or the NULL token
        # Separates tokens by whitespace or commas (returning commas as part of the list)
        # Discards all the LC3 end of line comments, discards empty lines / comment only lines
        # For quoted strings used by the .STRINGZ directive, the returned token preserves opening/closing quote marks 
        # but converts all internal escape sequences into their actual character value

    # Split into non-comment and comment portion
    uncommented_line = line.split(";")[0].strip("\n")
    tokens = line.split()
    return tokens

def match_syntax(line: str) -> bool:
    # Check if the provided line matches LC3 syntax
    # The standard form of LC3 syntax is
        # [label] opcode operands [; optional end of line comment]
    pass

def scan_operands(op_tokens: List[str]):
    pass

class BetterAssembler:
    def __init__(self, filepath: str, debug: bool = True):
        self.filepath = filepath
        self.debug = debug
        self.symbol_table = SymbolTable()
        self.src_line_count = 0     # Line in source file
        self.curr_addr = 0      # LC3 Addr of current instruction
    
    def __enter__(self):
        self.file = open(self.filepath)
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.file.close()

    def scan(self):
        """
        In the scanning phase of assembling:
            - Tokenize the line
            - Check if an opcode is present
                - Look at the first token. If it is not an opcode, assume it is a label.
            - Based on the opcode/label, write the metadata to a LineInfo dataclass
        """

        # Phase one of assembling
        for line_idx, line in enumerate(self.file):
            tokens = tokenize_line(line)
            if not tokens: continue
            
            if self.debug:  print(f"Line {line_idx} split into tokens {tokens}")

            if tokens[0] in opcodes:
                line_info = LineInfo(line_idx, None, None, tokens[0], tokens[1], tokens[2], tokens[3], tokens[4], None)
            else:
                # Assume it is a label
                pass

    def generate(self):
        # Phase 2 of assembling
        pass

class Assembler:
    def __init__(self, filepath: str, debug = True):
        """
        self.debug: whether assembler should run in debug mode (print intermediary calculation)
        self.location_counter: marks instruction idx in file (program start need not be at line 0 of file)
        self.symbol_table: maps self.location_counter to associated label
        """
        self.filepath = filepath
        self.debug = debug
        self.location_counter = None
        self.symbol_table = defaultdict(list)
        self.statements_to_machine_code = defaultdict()

    def scan_file(self, file: str):
        """
        Search for assembler directives
        Populate symbol table
        """
        
        # Step 2: Beginning at program entry point, search for lines with labels
        # LABEL OPCODE OPERANDS ; COMMENTS
        # Construct symbol table is a flag variable which tells us when to start recording for the symbol table
        construct_symbol_table = False
        with open(file) as fp:
            for line_idx, line in enumerate(fp):
                # Test whether the entry point is on this line
                if ".ORIG" in line:
                    if self.location_counter != None:
                        print("Warning: .ORIG appears twice")

                    self.location_counter = line_idx
                    construct_symbol_table = True

                    if self.debug == True: print("Found")

                
                # Test whether we should finish scanning
                if ".END" in line:
                    construct_symbol_table = False
                    break
            
                if construct_symbol_table:
                    # It is a feature of assembly syntax that the label comes first
                    whitespace_split = line.split()
                    if len(whitespace_split) > 0:
                        if whitespace_split[0] == ";":
                            # The line was a comment
                            pass
                        else:
                            label = whitespace_split[0]
                            self.symbol_table[label].append(self.location_counter)

                            if self.debug: print(f"Found label {label} in line {line}, added {self.location_counter} tp symbol_table[{label}]")

                            self.location_counter += 1
        if self.debug: pprint(f"Symbol table: {self.symbol_table}")

    def assemble_machine_code(self):
        pass

    # Parse an entire program
    def parse_program(self):
        print(self.current_line)
        print(self.skip())

    def skip(self):
        if self.current_line == re.match(r"\s+", self.current_line):
            print("Whitespace found")
        if self.current_line == re.match(r"(;).*[\n$]", self.current_line):
            print("Found single line comment")


# Set up the user-facing CLI interface
parser = argparse.ArgumentParser()
parser.add_argument("inputs", metavar = "INPUT", nargs = "*", help = "Input files to assemble")
args = parser.parse_args()

for i in args.inputs:
    assembler = BetterAssembler(i)
    with assembler as assemble:
        assembler.scan()