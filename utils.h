#pragma once
#include <stdio.h>
#include <stdint.h>
/* windows only */
#include <Windows.h>
#include <conio.h>  // _kbhit


extern HANDLE hStdin;
extern DWORD fdwMode, fdwOldMode;

void disable_input_buffering();
void restore_input_buffering();
void handle_interrupt(int signal); 
uint16_t check_key();