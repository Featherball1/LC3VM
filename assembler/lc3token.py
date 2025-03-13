from enum import Enum
from dataclasses import dataclass
from typing import List
import keywords

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
            if token in keywords.opcodes.keys():
                token_type = TokenType.OPCODE
                
                """CASE 2: We have encountered an assembler directive"""
            elif token.startswith("."):
                token_type = TokenType.ASSEMBLER_DIRECTIVE
                
                """CASE 3: We have encountered a register symbol"""
            elif token in keywords.registers.keys():
                token_type = TokenType.REGISTER
            
                """CASE 4: We have encountered a trap code"""
            elif token in keywords.trap_codes.keys():
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