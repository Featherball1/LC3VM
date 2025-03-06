import argparse
import re
from collections import defaultdict
from enum import Enum
from pprint import pprint

class Assembler:
    # Parse an entire assembly file
    """
    def parse_file(self, file: str):
        with open(file, "r") as i:
            self.current_line = i.read()
        # Interpret entire current input as a program
        print(self.current_line)
        self.parse_program()
        self.current_line = None
"""

    def __init__(self, debug = True):
        """
        self.debug: whether assembler should run in debug mode (print intermediary calculation)
        self.location_counter: marks instruction idx in file (program start need not be at line 0 of file)
        self.symbol_table: maps self.location_counter to associated label
        """
        self.debug = debug
        self.location_counter = None
        self.symbol_table = defaultdict(list)

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

parser = Assembler()
for i in args.inputs:
    parser.scan_file(i)