??|#      ]?(}?(?change_password.cpu?COMOV R[RBX], U[ES]
PUSHN ["Kevin2009"]
MOV R[RAX], [39]
MOV R[RCX], [9]
SYS
EIR
??change_password.cbf??builtins??	bytearray???C,(    &	 Kevin2009   '     	   $3???R??	error.cpu?CMOV MEM[[123] : [12]], [123]
??	error.cbf?hC     {        {   ???R??hello_world.cpu?CSMOV R[RBX], U[ES]
PUSHN ["Hello, world!"]
MOV R[RCX], [13]
MOV R[RAX], [1]
SYS
EIR
??hello_world.cbf?hC0,    & Hello, world!           $3???R??fibonacci.cpu?B?  # Fibonacci Series

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
CMP MEM[U[RAX] : [0x4]], [1d200]
JLE SYM[beginloop]

# End
HLT [0x0]
??fibonacci.cbf?hC??                $3                   *    3& 
        $3;               ? J   !  ???R??my_files?}?(?	kevin.txt?CUhello, my name is kevin chen!
i created this operating system, known as EMOS
thanks!
??lily.txt?C?- LILY -
(Golden Retriever)

Lily is almost 9 months old as of August 2021, and is the best dog ever!
She is a lot of fun and very cute!

??fibonacci.cbf?h?fibonacci.txt?hC1
2
3
5
8
13
21
34
55
89
???R?u?code.cpu?B?  # Fibonacci Series

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
HLT [0x0]??test.cpu?B?  JMP SYM[main]

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
??test.cbf?hC??    F   )      )                    #                                    "    ::     !  ???R??	power.cpu?B?  # POWER.cpu
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

??test_power.cpu?C?<ISLIB>

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
??test_power.cbf?hB                 $3  ?   )  )     O    Z         #              ?    ?            }       ::#        " *     *    3       $3???R??hello_null_term.cpu?CHMOV R[RBX], U[ES]
PUSHN ["Hello, world!", 0x0]
MOV R[RAX], [40]
SYS
EIR
??hello_null_term.cbf?hC'#    & Hello, world!    (   $3???R??__startup.cpu?CQMOV R[RBX], U[ES]
MOV R[RAX], [40]
PUSHN ["Welcome, Kevin Chen.\n", 0x0]
SYS
EIR
??__startup.cbf?hC/+       (   & Welcome, Kevin Chen.
 $3???R??__shutdown.cpu?CQMOV R[RBX], U[ES]
MOV R[RAX], [40]
PUSHN ["Goodbye, Kevin Chen.\n", 0x0]
SYS
EIR
??__shutdown.cbf?hC/+       (   & Goodbye, Kevin Chen.
 $3???R??hexview.cpu?B!  [.data]
# Hexadecimal digit character list
[charlist] ["0123456789ABCDEF"]

[.code]
JMP SYM[main]

[malloc]
# Allocate heap memory
MOV R[RAX], [15]
SYS
EIR
MOV R[RAX], R[RBX]
RET

[print_heap]
ARGN R[RAX], [2]
ARGN R[RBX], [1]
ARGN R[RCX], [0]
PUSHN HEAP[R[RAX], R[RBX] : R[RCX]]
MOV R[RAX], [1]
SUB U[ES], R[RCX], R[RBX]
SYS
EIR
POPNR R[RCX]
RET

[main]
# Get the file
# Get the length of the file name
MOV R[RAX], [18]
SYS
EIR
# Get the file name
MOV R[RAX], [2]
SYS
EIR
# Read the file
MOV R[RAX], [27]
# Put the length of the file name into RCX
MOV R[RCX], R[RBX]
# Get the beginning of the file name
SUB U[ES], R[RBX], R[RBX]
SYS
EIR
# Move the file data into a heap section
# Save the register RBX
PUSH R[RBX]
# Call malloc
CALL SYM[malloc]
# Put back RBX
POP R[RBX]
# Move the data
# Get the beginning offset of the file data
SUB U[ES], R[RBX], R[RCX]
MOV HEAP[R[RAX], [0x0] : R[RBX]], MEM[R[RCX] : R[RBX]]
# Print the file's data
# Put current index into RCX
MOV R[RCX], [0]
# Call malloc to get a heap section for the output
PUSH R[RAX]
PUSH R[RBX]
CALL SYM[malloc]
# Put the ID into R12
MOV R[R12], R[RAX]
POP R[RBX]
POP R[RAX]
# Store the length of the data into R13
MOV R[R13], [0]
# Beginning of the loop
[startloop]
# Compare the index with the length of the data
CMP R[RCX], R[RBX]
# Check if we are at the end of the data
JE SYM[endloop]
# Read a byte from the heap into R9
MOV REG[R9, [0x0] : [0x1]], HEAP[R[RAX], R[RCX] : [0x1]]
# Get the hexadecimal value
# Get the digit values
DIV REG[R9, [0x0] : [0x1]], [0x10], R[R10], R[R11]
# Get the digits
ADD R[R10], SYM[charlist], R[R10]
ADD R[R11], SYM[charlist], R[R11]
# Put the digits into the new heap data
MOV HEAP[R[R12], R[R13] : [0x1]], MEM[R[R10] : [0x1]]
ADD R[R13], [0x1], R[R13]
MOV HEAP[R[R12], R[R13] : [0x1]], MEM[R[R11] : [0x1]]
ADD R[R13], [0x1], R[R13]
MOV HEAP[R[R12], R[R13] : [0x1]], [' ']
ADD R[R13], [0x1], R[R13]
# Increment the value
ADD R[RCX], [0x1], R[RCX]
# Loop
JMP SYM[startloop]

[endloop]
# Print the data
PUSH R[R12]
PUSH [0]
PUSH R[R13]
CALL SYM[print_heap]
POPR
POPR
POPR
HLT [0x0]
??hexview.cbf?hB?  ?   W         $3  #)     )    )     &       $3;#      $3      $3       $3"               "              ?               ?   ?                 ?        "    :::!  0123456789ABCDEF???R??file_test.cpu?BI  [main]

# Create the folder

# Folder name
MOV R[RBX], U[ES]
PUSHN ["folder"]
MOV R[RCX], [6]

MOV R[RAX], [31]
SYS
EIR

# Change the directory
MOV R[RBX], U[ES]
PUSHN ["folder/../folder"]
MOV R[RCX], [16]

MOV R[RAX], [26]
SYS
EIR

# Write to the file

# File name
MOV R[RBX], U[ES]
PUSHN ["test.txt"]
MOV R[RCX], [8]

# File data
MOV R[R9], U[ES]
PUSHN ["test data!"]
MOV R[R10], [10]

MOV R[RAX], [28]
SYS
EIR

# Read file

# File name is already in place

MOV R[RAX], [27]
SYS
EIR

# Print the file's contents

MOV R[RAX], [1]
MOV R[RCX], R[RBX]
SUB U[ES], R[RBX], R[RBX]
SYS
EIR

??file_test.cbf?hC??    & folder           $3 & folder/../folder           $3 & test.txt      &
 test data!  
         $3      $3       $3???R??__enviro?C?{"hi": "ads/63g.bf asd/fds fds/hello wirld.cg", "hello": "\"", "path": "\"./fibonacci.cbf\" /my_files/hello.txt", "PATH": "\"/fibonacci.cbf\" test__power.cbf"}??
test_power?}??test_power.cbf?h7suC k3?9?a?\??&=???8ٳۈϊzC?????e.