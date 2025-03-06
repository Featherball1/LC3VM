
; Basic lc3 program.

; Semi-colons are used to create comments.

			.ORIG x3000

			LEA R0, HELLOWORLD
			PUTS
			HALT
	
HELLOWORLD	.STRINGZ "Hello World\n"

			.END