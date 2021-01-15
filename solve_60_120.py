import grpc
import question_pb2
import question_pb2_grpc
import contest_pb2
import contest_pb2_grpc
import time
import numpy as np

_HOST = '47.103.23.116'
_QUESTION_PORT = '56701'
_CONTEST_PORT = '56702'

flag = -1
stock = []
sessionKey = ''
stock_num = 351

max_exposure = 0.1
single_limit = 0.1
mean_short_num = 30
mean_long_num = 120
leverage = 1.9
operate_percent = 0.001
valid_stock = []

def submit_answer(sequence, positions):
    global sessionKey
    with grpc.insecure_channel("{0}:{1}".format(_HOST, _CONTEST_PORT)) as channel:
        client = contest_pb2_grpc.ContestStub(channel=channel)
        response = client.submit_answer(contest_pb2.AnswerRequest(user_id=95,user_pin='NWWrsIMf',\
                session_key=sessionKey, sequence=sequence, positions=positions))
        print("sequence:{}  result:{}  reason:{}".format(sequence, response.accepted, response.reason))


def get_question():
    t1 = time.time()
    global flag
    print()
    print()
    print()
    print()
    print("******************start asking sequence:{}*********************".format(flag+1))
    try:
        with grpc.insecure_channel("{0}:{1}".format(_HOST, _QUESTION_PORT)) as channel:
            client = question_pb2_grpc.QuestionStub(channel=channel)
            response = client.get_question(question_pb2.QuestionRequest(user_id=95,sequence=flag+1))
    except Exception as e:
        print(str(e))
        return
    print("****************sequence:{}  now_capital:{}***********".format(response.sequence, response.capital))
    user_id = response.user_id
    sequence = response.sequence
    has_next_question = response.has_next_question
    capital = response.capital
    dailystk = response.dailystk
    positions = response.positions
    if sequence == -1:
        return
    
    global stock
    global valid_stock
    if sequence != flag:
        if flag == -1:
            for i in range(stock_num):
                stock.append(np.array([dailystk[i].values]))
                positions.append(0)
                if dailystk[i].values[-1] * dailystk[i].values[-2] > capital * operate_percent:
                    valid_stock.append(1)
                else:
                    valid_stock.append(0)
            print('sequence:{} submit_positions:{}'.format(sequence, positions))
            #submit_answer(sequence, positions)            
            try:
                with grpc.insecure_channel("{0}:{1}".format(_HOST, _CONTEST_PORT)) as channel:
                    client = contest_pb2_grpc.ContestStub(channel=channel)
                    response = client.submit_answer(contest_pb2.AnswerRequest(user_id=95,user_pin='NWWrsIMf',\
                            session_key=sessionKey, sequence=sequence, positions=positions))
                print("sequence:{}  result:{}  reason:{}".format(sequence, response.accepted, response.reason))
            except Exception as e:
                print(str(e))
                return
        else:
            print('sequence:{} pre_positions:{} pre_capital:{}'.format(sequence, positions, capital))
            long_value = 0
            short_value = 0
            long_operation = []
            short_operation = []
            clear_long = []
            clear_short = []
            print(valid_stock)
            for i in range(stock_num):     
                if valid_stock[i] == 0:
                    continue
                pos = positions[i]
                stock[i] = np.concatenate((stock[i], np.array([dailystk[i].values])), axis=0)
                if pos > 0:
                    long_value += pos * stock[i][-1, -2]
                elif pos < 0:
                    short_value += pos * stock[i][-1, -2]

                if stock[i].shape[0] > max(mean_short_num, mean_long_num):
                    mean_long_value = stock[i][-mean_long_num:, -2].mean()
                    mean_short_value = stock[i][-mean_short_num:, -2].mean()
                    if pos == 0 and (mean_short_value - mean_long_value) / mean_long_value > 0.1:
                        if ((stock[i][-1, -3] - mean_long_value) / mean_long_value < 0.03 and \
                                abs(stock[i][-1, -2] * positions[i]) < capital * (single_limit - 4 * operate_percent)):
                            long_operation.append(i)

                        elif (stock[i][-1, -4] - mean_short_value) / mean_short_value > 0.2 and \
                                abs(stock[i][-1, -2] * positions[i]) < capital * (single_limit - 4 * operate_percent):
                            short_operation.append(i)
                        
                    elif pos < 0 and ((stock[i][-1, -3] - mean_long_value) / mean_long_value < 0.05 and \
                                (stock[i][-1, -4] - mean_short_value) / mean_short_value > 0.25):
                        clear_short.append(i)

                    elif pos > 0 and ((stock[i][-1, -4] - mean_short_value) / mean_short_value > 0.1 or \
                                (mean_long_value - stock[i][-1, -3]) / mean_long_value > 0.05):
                        clear_long.append(i)

            left = capital - long_value - short_value
            long_num = min(len(long_operation) + len(clear_short), len(short_operation) + len(clear_long))
            short_num = min(len(long_operation) + len(clear_short), len(short_operation) + len(clear_long))
            if long_value > short_value:
                long_num -= (long_value - short_value) / (capital * operate_percent)
            else:
                short_num -= (short_value - long_value) / (capital * operate_percent)
            
            pos = 0
            while pos < long_num:
                if pos < len(clear_short):
                    index = clear_short[pos] 
                    left += positions[index] * stock[index][-1, -2]
                    positions[index] = 0
                else:
                    index = long_operation[pos-len(clear_short)]
                    positions[index] = operate_percent * capital / stock[index][-1, -2]
                    left -= positions[index] * stock[index][-1, -2]
                pos += 1

            pos = 0
            while pos < short_num:
                if pos < len(clear_long):
                    index = clear_long[pos] 
                    left += positions[index] * stock[index][-1, -2]
                    positions[index] = 0
                else:
                    index = short_operation[pos-len(clear_long)]
                    positions[index] = operate_percent * capital / stock[index][-1, -2]
                    left -= positions[index] * stock[index][-1, -2]
                pos += 1

            print('sequence:{} submit_positions:{}'.format(sequence, positions))
            #submit_answer(sequence, positions)            
            try:
                with grpc.insecure_channel("{0}:{1}".format(_HOST, _CONTEST_PORT)) as channel:
                    client = contest_pb2_grpc.ContestStub(channel=channel)
                    response = client.submit_answer(contest_pb2.AnswerRequest(user_id=95,user_pin='NWWrsIMf',\
                            session_key=sessionKey, sequence=sequence, positions=positions))
                print("sequence:{}  result:{}  reason:{}".format(sequence, response.accepted, response.reason))
            except Exception as e:
                print(str(e))
                return

        flag = sequence
    t2 = time.time()
    print("***********end asking sequence:{} time consuming:{:.2}**************".format(flag+1, t2-t1))


def login():
    with grpc.insecure_channel("{0}:{1}".format(_HOST, _CONTEST_PORT)) as channel:
        client = contest_pb2_grpc.ContestStub(channel=channel)
        response = client.login(contest_pb2.LoginRequest(user_id=95,user_pin='NWWrsIMf'))
    global sessionKey
    sessionKey = response.session_key
    init_capital = response.init_capital
    success = response.success
    reason = response.reason
    print('Login...')
    print(sessionKey, init_capital, success, reason)    


def main():
    flag = -1
    stock = []
    login()
    for i in range(10000):
        time.sleep(4)
        get_question()

if __name__ == '__main__':
    main()
