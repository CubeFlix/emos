���      ]�(}�(�change_password.cpu�CNMOV R[RBX], U[ES]
PUSHN ["2xwwtizu"]
MOV R[RAX], [39]
MOV R[RCX], [8]
SYS
EIR
��change_password.cbf��builtins��	bytearray���C+'    & 2xwwtizu   '        $3���R��	error.cpu�CMOV MEM[[123] : [12]], [123]
��	error.cbf�hC     {        {   ���R��hello_world.cpu�CSMOV R[RBX], U[ES]
PUSHN ["Hello, world!"]
MOV R[RCX], [13]
MOV R[RAX], [1]
SYS
EIR
��hello_world.cbf�hC0,    & Hello, world!           $3���R��fibonacci.cpu�B�  # Fibonacci Series

<ISLIB>

[.code]

# Place current value into stack
MOV U[RAX], U[ES]
MOV MEM[U[ES] : [0x4]], [1]

# Place last value into stack
MOV U[RBX], U[ES]
MOV MEM[U[ES] : [0x4]], [1]

# Beginning loop
[beginloop]

# Write the current value
MOV R[R9], MEM[U[RAX] : [0x4]]

# Change the value into a string
LIB [0x0], [0x0]
EIR

# Add a newline
PUSHN ["
"]
ADD R[RBX], [0x1], R[RBX]

# Print the value
MOV R[RAX], [1]
MOV R[RCX], R[RBX]
SUB U[ES], R[RBX], R[RBX]
SYS
EIR
POPNR R[RCX]

# Update the values
MOV R[RAX], MEM[U[RBX] : [0x4]]
MOV MEM[U[RBX] : [0x4]], MEM[U[RAX] : [0x4]]
ADD R[RAX], MEM[U[RAX] : [0x4]], MEM[U[RAX] : [0x4]]

# Loop
CMP MEM[U[RAX] : [0x4]], [1d100]
JLE SYM[beginloop]

# End
HLT [0x0]��fibonacci.cbf�hC��                $3                   *    3& 
        $3;               d J   !  ���R��my_files�}��	kevin.txt�CUhello, my name is kevin chen!
i created this operating system, known as EMOS
thanks!
�s�code.cpu�B�  # Fibonacci Series

<ISLIB>

[.code]

# Place current value into stack
MOV U[RAX], U[ES]
MOV MEM[U[ES] : [0x4]], [1]

# Place last value into stack
MOV U[RBX], U[ES]
MOV MEM[U[ES] : [0x4]], [1]

# Beginning loop
[beginloop]

# Write the current value
MOV R[R9], MEM[U[RAX] : [0x4]]

# Change the value into a string
LIB [0x0], [0x0]
EIR

# Add a newline
PUSHN ["
"]
ADD R[RBX], [0x1], R[RBX]

# Print the value
MOV R[RAX], [1]
MOV R[RCX], R[RBX]
SUB U[ES], R[RBX], R[RBX]
SYS
EIR
POPNR R[RCX]

# Update the values
MOV R[RAX], MEM[U[RBX] : [0x4]]
MOV MEM[U[RBX] : [0x4]], MEM[U[RAX] : [0x4]]
ADD R[RAX], MEM[U[RAX] : [0x4]], MEM[U[RAX] : [0x4]]

# Loop
CMP MEM[U[RAX] : [0x4]], [1d100]
JLE SYM[beginloop]

# End
HLT [0x0]��test.cpu�B�  JMP SYM[main]

[sum]
ARGN REG[RAX, [0x0] : [0x4]], [0x1]
ARGN REG[RBX, [0x0] : [0x4]], [0x0]
ADD REG[RAX, [0x0] : [0x4]], REG[RBX, [0x0] : [0x4]], REG[RAX, [0x0] : [0x4]]
RET

[main]
PUSH [1]
PUSH [2]
SUB REG[ES, [0x4] : [0x4]], [0x8], REG[RAX, [0x0] : [0x4]]
SUB REG[ES, [0x4] : [0x4]], [0x4], REG[RBX, [0x0] : [0x4]]
PUSH MEM[REG[RAX, [0x0] : [0x4]] : [0x4]]
PUSH MEM[REG[RBX, [0x0] : [0x4]] : [0x4]]
CALL SYM[sum]
POPR
POPR
PUSH REG[RAX, [0x0] : [0x4]]
HLT [0x0]
��test.cbf�hC��    F   )      )                    #                                    "    ::     !  ���R��	power.cpu�B�  # POWER.cpu
# Function to take one number to the power of another number, or a^b.
# 
# Pseudocode:
# int power(int a, int b)
# {
# if (b == 0)
# {
# return 1;
# }
# 
# int answer = a;
# int i = 1;
# while (i < b)
# {
# answer = answer * a;
# i = i + 1;
# }
# return answer;
# }

[power]
# Get a
ARGN R[RAX], [0x1]
# Get b
ARGN R[RBX], [0x0]

# Check if b is 0
CMP R[RBX], [0x0]
JE SYM[power-zerocmp]
JNE SYM[power-notzerocmp]

# Value of b is zero
[power-zerocmp]
MOV R[RAX], [1]
RET

# Value of b is not zero, continue power
[power-notzerocmp]
# Define answer
MOV U[RAX], U[ES]
MOV MEM[U[ES] : [0x4]], R[RAX]
# Define i
MOV U[RBX], U[ES]
MOV MEM[U[ES] : [0x4]], [1]

# Power loop
[power-loop]
# Compare the value of i and b
CMP MEM[U[RBX] : [0x4]], R[RBX]
JL SYM[power-continueloop]
JGE SYM[power-return]

# Power continue loop
[power-continueloop]
# Multiply answer by a
MUL MEM[U[RAX] : [0x4]], R[RAX], MEM[U[RAX] : [0x4]]
# Increment i
ADD MEM[U[RBX] : [0x4]], [0x1], MEM[U[RBX] : [0x4]]
# Continue power loop
JMP SYM[power-loop]

# Power return
[power-return]
# Return answer
# Move answer into RAX
MOV R[RAX], MEM[U[RAX] : [0x4]]
# Remove answer and i
POPR
POPR
# Return
RET

��test_power.cpu�C�<ISLIB>

JMP SYM[main]

<"power.cpu">

[main]
PUSH [5]
PUSH [3]
CALL SYM[power]

MOV R[R9], R[RAX]
LIB [0x0], [0x0]
EIR

MOV R[RAX], [1]
MOV R[RCX], R[RBX]
SUB U[ES], R[RBX], R[RBX]
SYS
EIR
��test_power.cbf�hB                 $3  �   )  )     O    Z         #              �    �            }       ::#        " *     *    3       $3���R��hello_null_term.cpu�CHMOV R[RBX], U[ES]
PUSHN ["Hello, world!", 0x0]
MOV R[RAX], [40]
SYS
EIR
��hello_null_term.cbf�hC'#    & Hello, world!    (   $3���R��__startup.cpu�CQMOV R[RBX], U[ES]
MOV R[RAX], [40]
PUSHN ["Welcome, Kevin Chen.\n", 0x0]
SYS
EIR
��__startup.cbf�hC/+       (   & Welcome, Kevin Chen.
 $3���R��__shutdown.cpu�CQMOV R[RBX], U[ES]
MOV R[RAX], [40]
PUSHN ["Goodbye, Kevin Chen.\n", 0x0]
SYS
EIR
��__shutdown.cbf�hC/+       (   & Goodbye, Kevin Chen.
 $3���R��fibonacci.txt�hC1
2
3
5
8
13
21
34
55
89
���R�uC ��vB��N�_e��f�#�6(9s���悁?�O�e.