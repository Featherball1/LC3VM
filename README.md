# LC3VM

Goal:
	- Create a VM that simulates the LC-3 educational compute rarchitecture

LC-3 has
	- 65536 memory locations which store 16 bit values (total storage 128KB)
	- 10 total 16-bit registers
		- 8 general purpose registers (R0-R7)
		- 1 program counter (PC)
		- 1 condition flags (COND)
	- 16 opcodes
		- Each opcode represents one task that the CPU can do
	- 3 condition flags
		- Condition flags are used for the CPU to signal various situations
		- In LC-3 they indicate the sign of the previous calculation
	- Two memory mapped registers
		- The keyboard status register KBSR and keyboard data register KBDR
		- KBSR indicates whether a key has been pressed
		- KBDR identifies which key was pressed
		- Memory mapped registers are typically used to interact with special hardware devices
		- They are not accessible from the normal register table, and a special address is reserved for them in memory
		- To read and write to these registers, just read and write to their memory location


A tool called an assembler translates each assembly instruction into a 16-bit binary instruction
that the VM can understand. This is our machine code. We will also build an assembler. 