import pyrtl

# Define inputs and outputs
in_bit = pyrtl.Input(1, 'in_bit')      # Single-bit input
reset = pyrtl.Input(1, 'reset')        # Reset signal
detected = pyrtl.Output(1, 'detected') # Output: 1 when a certain pattern is detected

# Define 3-bit state register to represent 8 states
state = pyrtl.Register(3, 'state')

# Define constants for state encoding
S0 = pyrtl.Const(0b000)
S1 = pyrtl.Const(0b001)
S2 = pyrtl.Const(0b010)
S3 = pyrtl.Const(0b011)
S4 = pyrtl.Const(0b100)
S5 = pyrtl.Const(0b101)
S6 = pyrtl.Const(0b110)
S7 = pyrtl.Const(0b111)

# Define next state logic based on current state and input
with pyrtl.conditional_assignment:
    with reset:
        state.next |= S0
    with state == S0:
        with in_bit:
            state.next |= S1
        with ~in_bit:
            state.next |= S0
    with state == S1:
        with in_bit:
            state.next |= S2
        with ~in_bit:
            state.next |= S3
    with state == S2:
        with in_bit:
            state.next |= S4
        with ~in_bit:
            state.next |= S0
    with state == S3:
        with in_bit:
            state.next |= S5
        with ~in_bit:
            state.next |= S0
    with state == S4:
        with in_bit:
            state.next |= S6
        with ~in_bit:
            state.next |= S3
    with state == S5:
        with in_bit:
            state.next |= S2
        with ~in_bit:
            state.next |= S6
    with state == S6:
        with in_bit:
            state.next |= S7
        with ~in_bit:
            state.next |= S1
    with state == S7:
        with in_bit:
            state.next |= S0
        with ~in_bit:
            state.next |= S0

# Output condition: detected = 1 when in state S7
detected <<= state == S7