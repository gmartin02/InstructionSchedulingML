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
    def __init__(self, trace_instructions, S, N):
        self.all_instructions = list(trace_instructions)
        
        self.fake_rob = []
        self.dispatch_list = []
        self.issue_list = []
        self.execute_list = []

        self.trace = list(trace_instructions)
        self.total_instructions = len(trace_instructions)
        self.cycle = 0

        # parameters for machine learning
        self.N = N
        self.fetch_bandwidth = 2       # max instructions fetched per cycle
        self.dispatch_capacity = 16    # capacity for dispatch queue
        self.issue_capacity = 16       # capacity for issue queue
        self.issue_width = 2           # max instructions issued per cycle

        # for dependency: an instruction is “ready” only when its tag equals last_retired_tag+1
        self.last_retired_tag = -1
    def fake_retire(self):
        #changed to a while loop to treat more like a queue
        while self.fake_rob and self.fake_rob[0].state == WB:
            instr = self.fake_rob.pop(0)
            instr.state = 'Retire'
            instr.timing['Retire'] = self.cycle
            self.last_retired_tag = max(self.last_retired_tag, instr.tag)
            print(f"Cycle {self.cycle}: Retire - Instruction {instr.tag} (PC: {hex(instr.address)}) retire has been completed")

    def execute(self):
        new_ex_list = []
        for instr in self.execute_list:
            if instr.timing['EX'] is None:
                instr.timing['EX'] = self.cycle
                if instr.remaining_latency is None:
                    instr.remaining_latency = instr.exec_latency
            instr.remaining_latency -= 1
            print(f"Cycle {self.cycle}: Execute - Instr {instr.tag} remaining latency {instr.remaining_latency}")
            if instr.remaining_latency <= 0:
                instr.state = WB
                instr.timing['WB'] = self.cycle
                print(f"Cycle {self.cycle}: Execute - Instr {instr.tag} completed EX, moved to WB")
            else:
                new_ex_list.append(instr)
        self.execute_list = new_ex_list

    def issue(self):
        for instr in self.dispatch_list:
            if instr.state == IF:
                instr.state = ID
                if instr.timing['ID'] is None:
                    instr.timing['ID'] = self.cycle + 1
                print(f"Cycle {self.cycle}: Issue - Instr {instr.tag} converted from IF to ID")
        
        while len(self.issue_list) < self.issue_capacity and self.dispatch_list:
            instr = self.dispatch_list.pop(0)
            if instr.state == ID:
                instr.state = IS
                instr.remaining_latency = instr.exec_latency
                instr.timing['IS'] = self.cycle
                print(f"Cycle {self.cycle}: Issue - Instruction {instr.tag} (PC: {hex(instr.address)}) moved to IS")
                self.issue_list.append(instr)
        
        ready_instrs = [instr for instr in self.issue_list if instr.tag == self.last_retired_tag + 1]
        ready_instrs.sort(key=lambda x: x.tag)
        for instr in ready_instrs[:self.issue_width]:
            self.issue_list.remove(instr)
            instr.state = EX
            if instr.timing['EX'] is None:
                instr.timing['EX'] = self.cycle
            if instr.remaining_latency is None:
                instr.remaining_latency = instr.exec_latency
            self.execute_list.append(instr)
            print(f"Cycle {self.cycle}: Issue - Instr {instr.tag} issued to EX (IS duration = {self.cycle - instr.timing['IS']})")

    def dispatch(self):
        for instr in self.fake_rob:
            if instr.state == IF:
                instr.state = ID
                if instr.timing['ID'] is None:
                    instr.timing['ID'] = self.cycle
                print(f"Cycle {self.cycle}: Dispatch - Instr {instr.tag} converted from IF to ID in fake_rob")
        temp_list = [instr for instr in self.fake_rob if instr.state == ID]
        temp_list.sort(key=lambda x: x.tag)
        for instr in temp_list:
            if len(self.dispatch_list) < self.dispatch_capacity:
                if instr not in self.dispatch_list:
                    self.dispatch_list.append(instr)
                    print(f"Cycle {self.cycle}: Dispatch - Instr {instr.tag} dispatched to dispatch_list")

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

        out_lines = []
        out_lines.append(f"Total instructions: {self.total_instructions}")
        out_lines.append(f"Total cycles: {total_cycles}")
        out_lines.append(f"Average IPC: {ipc:.3f}\n")
        out_lines.append("Timing per instruction:")
        for instr in sorted(self.all_instructions, key=lambda x: x.tag):
            # compute timings for each instruction
            if_start = instr.timing['IF'] if instr.timing['IF'] is not None else 0
            id_start = instr.timing['ID'] if instr.timing['ID'] is not None else (if_start + 1)
            is_start = instr.timing['IS'] if instr.timing['IS'] is not None else (id_start + 1)
            ex_start = instr.timing['EX'] if instr.timing['EX'] is not None else (is_start + 1)
            wb_start = instr.timing['WB'] if instr.timing['WB'] is not None else (ex_start + 1)
            if_dur = id_start - if_start
            id_dur = is_start - id_start
            is_dur = ex_start - is_start
            ex_dur = wb_start - ex_start
            wb_dur = 1
            out_lines.append(f"{instr.tag} fu{{{instr.operation}}} src{{{instr.src1},{instr.src2}}} dst{{{instr.dest}}} " +
                f"IF{{{if_start},{if_dur}}} ID{{{id_start},{id_dur}}} IS{{{is_start},{is_dur}}} " +
                f"EX{{{ex_start},{ex_dur}}} WB{{{wb_start},{wb_dur}}}")
        
        with open("sim_output.txt", "w") as fout:
            for line in out_lines:
                fout.write(line + "\n")
        print("\nFinal statistics written to sim_output.txt")

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
    S = 2
    N = 8
    trace_filename = 'trace.txt'
    try:
        trace_instructions = read_trace(trace_filename)
    except FileNotFoundError:
        print(f"Error: Trace file '{trace_filename}' not found.")
        exit(1)

    sim = Simulator(trace_instructions, S, N)
    sim.run()
    sim.print_final_stats()
