N = 8 #Max size for queue sizes.
S = 2 #Scheduling queue size.

cycle = 0 #Cycle that program is on
trace_file = open("trace.txt", "r")
tag_counter = 0 #Tag counter.
RF = []

IF, ID, IS, EX, WB = range(5)

fetch = []
dispatch = []
issue = []
execute = []
fakeROB = []
disposal = []

class Instruction:
    def __init__(self, address, operation, dest, src1, src2):
        global tag_counter, cycle
        self.address = address
        self.operation = operation

        self.dest_o = dest #// The difference bewteen <reg>_o and <reg> is that <reg>_o is the original unmodified register and the other one gets overwritten with a tag later on.
        self.src1_o = src1
        self.src2_o = src2

        self.dest = dest
        self.src1 = src1
        self.src2 = src2

        self.state = IF
        self.tag = tag_counter
        self.IF_cycle = cycle

        self.IF_duration = 1 
        self.ID_duration = 0 
        self.IS_duration = 0 
        self.EX_duration = 0 
        self.WB_duration = 0 
        self.ID_cycle = 0
        self.IS_cycle = 0
        self.EX_cycle = 0
        self.WB_cycle = 0
        self.exec_latency = 0

        self.src1_flag = 1
        self.src2_flag = 1

        self.depend_1 = None
        self.depend_2 = None

        if operation == 0:
            self.exec_latency = 1
            self.EX_duration = 1
        elif operation == 1:
            self.exec_latency = 2
            self.EX_duration = 2
        else:
            self.exec_latency = 5
            self.EX_duration = 5

def init_RF():
    global RF
    RF = [[i, 0] for i in range(128)]
    #0 means resgister is unused or ready.

def ClearROB():
    disposal.clear()

#Check fakeROB for any instructions in the WB state and remove them.
def FakeRetire():
    global fakeROB, disposal, cycle
    if not fakeROB:
        return
    i = 0
    while i < len(fakeROB):
        if fakeROB[i].state != WB:
            return
        ins = fakeROB.pop(i)
        print(f"{ins.tag} fu{{{ins.operation}}} src{{{ins.src1_o},{ins.src2_o}}} dst{{{ins.dest_o}}} "
              f"IF{{{ins.IF_cycle},{ins.IF_duration}}} ID{{{ins.ID_cycle},{ins.IS_cycle - ins.ID_cycle}}} "
              f"IS{{{ins.IS_cycle},{ins.EX_cycle - ins.IS_cycle}}} EX{{{ins.EX_cycle},{ins.WB_cycle - ins.EX_cycle}}} "
              f"WB{{{ins.WB_cycle},1}}")
        disposal.append(ins)

#Each instruction has an operation value (0, 1, 2) which describe its execution latency, or how many cycles we delay it in the simulator.
#Once the instruction passes through its required cycles, we remove it from the execute queue.
def Execute():
    global execute, cycle
    new_execute = []
    for ins in execute:
        if ins.exec_latency <= 0:
            ins.state = WB
            ins.WB_cycle = cycle
        else:
            ins.exec_latency -= 1
            new_execute.append(ins)
    execute[:] = new_execute

def Issue():
    global issue, execute, cycle
    temp = []
    i = 0
    while i < len(issue):
        ins = issue[i]
        if ins.depend_1 is not None and ins.src1_flag == 0:
            if ins.depend_1.state == WB:
                ins.src1_flag = 1
        if ins.depend_2 is not None and ins.src2_flag == 0:
            if ins.depend_2.state == WB:
                ins.src2_flag = 1

        if ins.src1_flag and ins.src2_flag and (len(execute) + len(temp) < N + 1):
            temp.append(ins)
            issue.pop(i)
        else:
            i += 1

    temp.sort(key=lambda x: x.tag)
    for ins in temp:
        ins.state = EX
        ins.EX_cycle = cycle
        ins.exec_latency -= 1
        execute.append(ins)

#Dispatch, but flagging takes place here in this version.
def Dispatch():
    global dispatch, issue, cycle
    temp = []
    if not dispatch:
        return

    if len(issue) < S:
        i = 0
        while i < len(dispatch):
            #Since the issue queue essentially contains only N instructions, we push only that amount.
            if len(issue) + len(temp) >= S:
                break
            ins = dispatch[i]
            RenameOps(ins)
            temp.append(ins)
            dispatch.pop(i)
    for ins in temp:
        ins.state = IS
        ins.IS_cycle = cycle
        issue.append(ins)

#Where the actual renaming takes place.
#If any one of the instruction's register is marked as -1, it doesn't have that register, and so there's nothing to rename.
def RenameOps(dispatched):
    global RF
    if dispatched.dest_o != "-1":
        reg = int(dispatched.dest_o) #Here we assign a tag to the register in the RF.
        RF[reg][0] = dispatched.tag
        dispatched.dest = str(RF[reg][0])
    if dispatched.src1_o != "-1":
        reg = int(dispatched.src1_o)
        dispatched.src1 = str(RF[reg][0])
    if dispatched.src2_o != "-1":
        reg = int(dispatched.src2_o)
        dispatched.src2 = str(RF[reg][0])

def FetchtoDispatch():
    global fetch, dispatch, cycle
    if not fetch:
        return
    while fetch and len(dispatch) < N:
        ins = fetch.pop(0)
        ins.state = ID
        ins.ID_cycle = cycle
        dispatch.append(ins)

def Fetch():
    global fetch, fakeROB, trace_file, tag_counter, cycle
    #while (dispatch.size() < 2*N) { // Check if the dispatch queue is full. If yes, we skip fetching for the time-being.
    while len(fetch) < N and len(fakeROB) < 1024:
        line = trace_file.readline()
        if not line: #The trace file has a weird empty line at the end which throws off the entire code, so I made sure to check for empty lines.
            trace_file.close()
            return
        line = line.strip()
        if line == "": #If the file has reached the end, we close it.
            trace_file.close()
            return

        parts = line.split()
        if len(parts) < 5:
            continue

        address = int(parts[0], 16) #Interpret string as hex and store it as integer, might have to change this to store as actual hex.
        operation = int(parts[1])
        dest = parts[2]
        src1 = parts[3]
        src2 = parts[4]

        ins = Instruction(address, operation, dest, src1, src2)
        for prev in reversed(fakeROB):
            if prev.dest_o == src1 and prev.state != WB and prev.dest_o != "-1" and prev.tag < ins.tag:
                ins.depend_1 = prev
                ins.src1_flag = 0
                break
        for prev in reversed(fakeROB):
            if prev.dest_o == src2 and prev.state != WB and prev.dest_o != "-1" and prev.tag < ins.tag:
                ins.depend_2 = prev
                ins.src2_flag = 0
                break

        ins.IF_cycle = cycle
        fetch.append(ins) #Add to dispatch queue.
        fakeROB.append(ins) #Add to fakeROB
        tag_counter += 1

def AdvanceCycle():
    global cycle
    #If there are no more instructions left, end calculations
    if isEmpty():
        return False
    #If there are more instructions to calculate, increment to next cycle and continue
    else:
        cycle += 1
        return True

#Checks if fakeROB empty. This means there are no longer any instructons left in the pipeline!
def isEmpty():
    global fakeROB, execute, issue, dispatch, fetch, trace_file
    if fakeROB:
        return False
    if execute:
        return False
    if issue:
        return False
    if dispatch:
        return False
    if fetch:
        return False
    if not trace_file.closed:
        return False
    return True

def main():
    global cycle, tag_counter
    init_RF()
    
    while True:
        FakeRetire()
        Execute()
        Issue()
        Dispatch()
        FetchtoDispatch()
        if not trace_file.closed:
            Fetch()
        if not AdvanceCycle():
            break

    print("number of instructions =", tag_counter)
    print("number of cycles       =", cycle)
    ipc = float(tag_counter) / float(cycle) if cycle != 0 else 0.0
    print("IPC                    = {:.5f}".format(ipc))
    
    ClearROB()

if __name__ == "__main__":
    main()
    