IF, ID, IS, EX, WB = range(5)

class Instruction:
    fetch_count = 0

    def __init__(self, address, operation, dest, src1, src2):
        self.address = address
        self.operation = operation
        self.dest = dest
        self.src1 = src1
        self.src2 = src2

        self.tag = Instruction.fetch_count
        Instruction.fetch_count += 1

        self.state = IF

        # set execution latency based on operation type
        if self.operation == 0:
            self.exec_latency = 1
        elif self.operation == 1:
            self.exec_latency = 2
        elif self.operation == 2:
            self.exec_latency = 5

        self.remaining_latency = None

        # timing information for each stage
        self.timing = {
            'IF': None,
            'ID': None,
            'IS': None,
            'EX': None,
            'WB': None,
            'Retire': None
        }

class Simulator:
    def __init__(self, trace_instructions):
        self.all_instructions = list(trace_instructions)
        
        self.fake_rob = []
        self.dispatch_list = []
        self.issue_list = []
        self.execute_list = []

        self.trace = list(trace_instructions)
        self.total_instructions = len(trace_instructions)
        self.cycle = 0

        # parameters for machine learning
        self.fetch_bandwidth = 2       # max instructions fetched per cycle
        self.dispatch_capacity = 16    # capacity for dispatch queue
        self.issue_capacity = 16       # capacity for issue queue
        self.issue_width = 2           # max instructions issued per cycle

    def fake_retire(self):
        print("")

    def execute(self):
        print("")

    def issue(self):
       print("")

    def dispatch(self):
        print("")

    def fetch(self):
        for instr in self.dispatch_list:
            if instr.state == IF:
                instr.state = ID
                if instr.timing['ID'] is None:
                    instr.timing['ID'] = self.cycle
                print(f"Cycle {self.cycle}: Fetch - Instruction {instr.tag} (PC: {hex(instr.address)}) went from IF to ID")

        fetch_count = 0
        while self.trace and fetch_count < self.fetch_bandwidth and len(self.dispatch_list) < self.dispatch_capacity:
            instr = self.trace.pop(0)
            instr.state = IF
            if instr.timing['IF'] is None:
                instr.timing['IF'] = self.cycle
            self.fake_rob.append(instr)
            self.dispatch_list.append(instr)
            fetch_count += 1
            print(f"Cycle {self.cycle}: Fetch - Fetched new Instruction {instr.tag} (PC: {hex(instr.address)}) into fake-ROB and dispatch_list")
        return fetch_count

    def advance_cycle(self):
        self.cycle += 1
        print(f"\nGoing to Cycle {self.cycle}")
        if (not self.trace and not self.fake_rob and 
            not self.dispatch_list and not self.issue_list and not self.execute_list):
            return False
        return True

    def run(self):
       # main simulation loop
        while True:
            self.fake_retire()
            self.execute()
            self.issue()
            self.dispatch()
            self.fetch()
            
            if (not self.trace and not self.fake_rob and 
                not self.dispatch_list and not self.issue_list and not self.execute_list):
                # simulation done
                break
            if not self.advance_cycle():
                break

    def print_final_stats(self):
        total_cycles = self.cycle
        ipc = self.total_instructions / total_cycles if total_cycles > 0 else 0

        print(f"Total instructions: {self.total_instructions}")
        print(f"Total cycles: {total_cycles}")
        print(f"Average IPC: {ipc:.3f}\n")
        print("Timing per instruction:")
        
        for instr in sorted(self.all_instructions, key=lambda x: x.tag):
            # compute timings for each instruction
            if_start = instr.timing['IF'] if instr.timing['IF'] is not None else 0
            id_start = instr.timing['ID'] if instr.timing['ID'] is not None else (if_start + 1)
            is_start = instr.timing['IS'] if instr.timing['IS'] is not None else (id_start + 1)
            ex_start = instr.timing['EX_start'] if instr.timing['EX_start'] is not None else (is_start + 1)
            wb_start = instr.timing['WB'] if instr.timing['WB'] is not None else (ex_start + 1)
            if_dur = id_start - if_start
            id_dur = is_start - id_start
            is_dur = ex_start - is_start
            ex_dur = wb_start - ex_start
            wb_dur = 1
            
            print(f"{instr.tag} fu{{{instr.operation}}} src{{{instr.src1},{instr.src2}}} dst{{{instr.dest}}} "
                  f"IF{{{if_start},{if_dur}}} ID{{{id_start},{id_dur}}} IS{{{is_start},{is_dur}}} "
                  f"EX{{{ex_start},{ex_dur}}} WB{{{wb_start},{wb_dur}}}")

def read_trace(filename):
    instructions = []

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            PC = parts[0]
            operation = int(parts[1])
            dest_reg = int(parts[2])
            src1_reg = int(parts[3])
            src2_reg = int(parts[4])
           
            dest = str(dest_reg)
            src1 = str(src1_reg)
            src2 = str(src2_reg)
            
            # convert PC from hex to int
            instr = Instruction(int(PC, 16), operation, dest, src1, src2)
            
            instructions.append(instr)
    return instructions

if __name__ == '__main__':
    trace_filename = 'trace.txt'
    try:
        trace_instructions = read_trace(trace_filename)
    except FileNotFoundError:
        print(f"Error: Trace file '{trace_filename}' not found.")
        exit(1)

    sim = Simulator(trace_instructions)
    sim.run()
    sim.print_final_stats()