'''
Note: This script contacts the server through Port 5000. It is known that
National Instrument's LabView also uses this portal. So tagsrv.exe needs to be
terminated first. This is not a problem on Raspberry Pi.
'''


import socket
import types
import time
import datetime
import threading
import os
#import decode_data
import copy
import select

import queue as Q
import numpy as np
import errno
from struct import *

from pandas import read_excel
import plotKlems as pk

###info
# this file utilize multi thread to solve the delay of saving data.


###for testing individual sensors.
doTestSensor = False
testStart = 48 # Print reading from this patch.
testEnd = 64 #Print reading up to this patch.

# These are usually used together.
doPlot = True
doPlotBlock = False
#doPlot = False
#doMannual = True #This way reading data is triggered mannually.
doMannual = False
doClean = True #This turns on emptying the server buffer before receiving data to get rid of old readings piled up.

#ServerIP and port config.
PORT = 5000    #udp protocol port
ServerIp = '192.168.1.193'

# file saved path.
FILEPATH = './'  #data saved path

#plot config.
#PLOT_NUM =160  # x-axis totally number is 600*PLOT_NUM
#PLOT_COUNT = 10 # figure is updated every 0.06*PLOT_COUNT s

# sensor config
sensor_ip_list =[]

sensor_ip_list.append('192.168.1.110')
#sensor_ip_list.append('192.168.1.107')
#sensor_ip_list.append('192.168.1.232')
#sensor_ip_list.append('192.168.1.244')

#data_time = 4000000 #receiv data time limit, the unit is seconds, 0 means receive data all the time.
data_time = 60

GAIN = 80
#GAIN = 20
RATE = 10000  # sampling rate
ERR_LEN = 800 # if one sensor received data legth les then REE_LEN reconfig sensor
#*************config end*************

if doPlot:
    klems_idx = pk.assignKlemsPatch() # Python var is not scoped in a block

queue = []
for ii in range(len(sensor_ip_list)):
    queue.append(Q.Queue(0))

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #UDP
server_address = (ServerIp, PORT)

server_socket.bind(server_address)

"""Read conversion factor for the SLAB"""
vec = np.loadtxt("conversion_l_over_e.txt")
conv_fac = np.diag(vec)
mapping = read_excel("mapping.xls", header=None).to_numpy()

def decode_config_message(msg_bit):
    """Decode and remove all non-ASCII char's."""
    return ''.join([x for x in msg_bit.decode() if ord(x) < 127 and ord(x) > 31])

def decodeVal_opt(low_b, high_b):
    low = int.from_bytes(low_b, byteorder='big', signed=False)
    high = int.from_bytes(high_b, byteorder='big', signed=False)
    expo = high >> 4
    frac = (low | high << 8) & 0xfff
    return 0.01 * 2**expo * frac

def decode_data(receive_data_bit):
    """Decode reading data from the OPT3001 sensors. (12 * 16 = ) 192 readings in total."""
    receive_data_lst = [bytes([i]) for i in receive_data_bit]
    readings = np.zeros(192)
    for aa in range(192):
        low_b = receive_data_lst[18 + 3 * aa]
        high_b = receive_data_lst[19 + 3 * aa]
        readings[aa] = decodeVal_opt(low_b, high_b)
    return readings

def all_receive_data(sensor_ip_list, time_lim):
    time_tag = get_time_tag()
    old_min = time_tag[14:16]
    file_date = time_tag[0:14]
    start_second = int(time.time());

    all_data  = []


    for ii in range(len(sensor_ip_list)):
        all_data.append([])  #initial data list
        all_data[ii] = ''

    s='''
    # initial plot info
    data_location_num = 0
    thread = threading.Thread(target=myplot, args=(len(sensor_ip_list),))
    thread.setDaemon(True)
    thread.start()
    '''
    server_socket.setblocking(0)
    data_flag = False
    initial_flag = True

    while True:
        time_tag = get_time_tag()
        new_min = time_tag[14:16]

        #time_limit
        now_second = int(time.time())
        if (time_lim >0) & (now_second - start_second > time_lim):
            sensor_stop(sensor_ip_list)
            #save file
            print("Save last file. Time elapsed: ", now_second - start_second)
            filename = file_date + new_min + '.txt'
            writ_data = copy.deepcopy(all_data)
            threading.Thread(target=save_file, args=(sensor_ip_list,filename,writ_data,)).start()
            break


        # save file. One per minute.
        if new_min != old_min:
            filename = file_date + old_min + '.txt'
            old_min = new_min
            file_date = time_tag[0:14]
            writ_data = copy.deepcopy(all_data)
            print("Start writing minute data.")
            threading.Thread(target=save_file, args=(sensor_ip_list,filename,writ_data,)).start()
			#set

            for data_id in range(len(sensor_ip_list)):
                if (len(all_data[data_id]) < ERR_LEN) and (initial_flag ==False):
                    print("Reconfig the sensor")
                    sensor_config_start(sensor_ip_list[data_id], GAIN, RATE)
            for ii in range(len(sensor_ip_list)):
                all_data[ii] = ''
            initial_flag = False

# receive sensor package
        try:
            if doClean:
                # clean all readings, and wait for 0.001 second to get fresh readings.
                empty_socket(server_socket)
                time.sleep(0.001)
            receive_data, client_address = server_socket.recvfrom(2048)
            data_flag = True
            time_tag = get_time_tag()
        except IOError as e:
            if e.errno == errno.EWOULDBLOCK:
                data_flag = False
            continue

        t1 = time.perf_counter()
        data_ip = str(client_address[0])

        if len(receive_data) < 100:
            #re_message = decode_data.decode_config_message(receive_data)
            re_message = decode_config_message(receive_data)
            if re_message in 'Sp':
                print("%s is stoped!"%data_ip)
            continue
        if data_ip in sensor_ip_list:
            data_location_num = sensor_ip_list.index(data_ip)
        else:
            print ('%s sensor still upload data!'%data_ip)
            continue

        #de_code_data =  decode_data.decode_data(receive_data)
        readings = decode_data(receive_data)
        illu = np.matmul(mapping, readings)
        luminance = np.matmul(conv_fac, illu)

        if doPlot:
            pk.plotKlems(luminance, klems_idx, 1, 1, None, 0.0, 0, -3, 1, doPlotBlock, 1.0) #view is from inside; blocking = doPlotBlock
            #makePlot(mapping, klems_idx, readings)
            #thread = threading.Thread(target=makePlot, args=(mapping, klems_idx, readings)) # Need to solve "QApplication was not created in the main() thread" issue.
            #thread.setDaemon(True)
            #thread.start()

        all_data[data_location_num] =all_data[data_location_num] + time_tag + np.array2string(luminance) +'\n'
        #all_data[data_location_num] =all_data[data_location_num] + time_tag + de_code_data +'\n'
        #print(readings[0])

        t2 = time.perf_counter()
        print("data process time is %f"%(t2-t1))

        if doTestSensor:
            print(readings[testStart:testEnd])
            input("continue?")

        if doMannual:
            #sensor_stop(sensor_ip_list)
            #server_socket.recvfrom(1024)
            s = input("continue? Put in 's' to stop")
            if s == 's':
                now_second = int(time.time())
                #save file
                print("Save last file. Time elapsed: ", now_second - start_second)
                filename = file_date + new_min + '.txt'
                writ_data = copy.deepcopy(all_data)
                threading.Thread(target=save_file, args=(sensor_ip_list,filename,writ_data,)).start()
                break
        # Wait for 1 second.
        #time.sleep(1)
def config_system():
    print ("\n*****config information***** \nGain =  %d , record time = %d seconds \nstarted sensor are : %s \n**************************\n" % (GAIN, data_time, str(sensor_ip_list)))
    for ii in sensor_ip_list:
        sensor_config_start(ii, GAIN, RATE )

def receive_one_data(sensor_ip_list, doPlotBlock = False):
    """Read one data from the SLAB. Only this and nothing else.
    The start and the termination of the connection and the reading process
    should be handled elsewhere."""

    time_tag = get_time_tag()
    old_min = time_tag[14:16]
    file_date = time_tag[0:14]
    start_second = int(time.time());

    all_data  = []

    for ii in range(len(sensor_ip_list)):
        all_data.append([])  #initial data list
        all_data[ii] = ''

    server_socket.setblocking(0)
    data_flag = False
    initial_flag = True

    # receive sensor package
    while True:
        try:
            empty_socket(server_socket)
            time.sleep(0.001)
            receive_data, client_address = server_socket.recvfrom(2048)
            data_flag = True
            time_tag = get_time_tag()
            print("Received!")

            data_ip = str(client_address[0])

            if len(receive_data) < 100:
                #re_message = decode_data.decode_config_message(receive_data)
                re_message = decode_config_message(receive_data)
                if re_message in 'Sp':
                    print("%s is stoped!"%data_ip)
                continue
            if data_ip in sensor_ip_list:
                data_location_num = sensor_ip_list.index(data_ip)
            else:
                print ('%s sensor still upload data!'%data_ip)
                continue
            break
        except IOError as e:
            if e.errno == errno.EWOULDBLOCK:
                data_flag = False
            continue

    #de_code_data =  decode_data.decode_data(receive_data)
    readings = decode_data(receive_data)
    illu = np.matmul(mapping, readings)
    luminance = np.matmul(conv_fac, illu)

    if doPlot:
        pk.plotKlems(luminance, klems_idx, 1, 1, None, 0.0, 0, -3, 1, doPlotBlock, 1.0) #view is from inside; blocking = doPlotBlock

    all_data[data_location_num] =all_data[data_location_num] + np.array2string(luminance) +'\n'
    #all_data[data_location_num] =all_data[data_location_num] + time_tag + de_code_data +'\n'
    #print(readings[0])

    """Save data"""
    now_second = int(time.time())
    time_tag = get_time_tag()
    new_min = time_tag[14:18]
    #save file
    print("Save last file. Time elapsed: ", now_second - start_second)
    filename = file_date + new_min + '.txt'
    writ_data = copy.deepcopy(all_data)
    threading.Thread(target=save_file, args=(sensor_ip_list,filename,writ_data,)).start()


def reconnect(ServerIp, PORT):
    """Reconnect"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #UDP
    server_address = (ServerIp, PORT)
    server_socket.bind(server_address)
    return server_socket

def close_connection():
    """Close the socket."""
    server_socket.close()

def makePlot(mapping, klems_idx, readings):
    illu = np.matmul(mapping, readings)
    pk.plotKlems(illu, klems_idx, 1, 1, None, 0.0, 0, -3, 1, doPlotBlock, 1.0) #view is from inside; blocking = doPlotBlock


def receive_data(sensor_ip, target_str):

    flag = False
    start_time = time.time()
    while True:
        receive_data, client_address = server_socket.recvfrom(65535)
        print(receive_data)
        print(client_address)
        #real_data = decode_data.decode_config_message(receive_data)
        real_data = decode_config_message(receive_data)
        print ('%s and message is %s'%(str(client_address[0]), real_data))

        if (str(client_address[0]) == sensor_ip) and target_str in real_data:
            flag = True
            break
        now_time = time.time()
        if now_time - start_time > 1:
            break

    return flag

def send_data(sensor_ip, data_str):

    sensor_address = (sensor_ip, PORT)
    server_socket.sendto(data_str.encode(),sensor_address)

def save_file(sensor_ip_list, filename, data_list):

    date = filename.split('_')[0]
    for count in range( len(sensor_ip_list)):
        if os.path.exists(FILEPATH + sensor_ip_list[count] +'/'+ date +'/') == False:
            os.makedirs(FILEPATH + sensor_ip_list[count] + '/'+ date)
        complete_filename = FILEPATH + sensor_ip_list[count] +'/' + date +'/' +filename
        print(complete_filename)
        datafile = open(complete_filename,'wb')
        print(len(data_list[count]))
        datafile.write(data_list[count].encode())
        datafile.close()

def get_time_tag():

    timenow = datetime.datetime.now()
    filename = str(timenow)
    filename = filename.replace(' ','_')
    filename = filename.replace(':','-')
    return filename

def empty_socket(sock):
    """remove the data present on the socket"""
    input = [sock]
    while 1:
        inputready, o, e = select.select(input,[],[], 0.0)
        if len(inputready)==0: break
        for s in inputready: s.recv(1)

def sensor_config_start(sensor_ip, GAIN, RATE):

    ZERO = chr(0)+chr(0)
    state = 0

    reset_com = 'r' + ZERO
    test_com ='t' + ZERO
    send_data(sensor_ip, reset_com)
    send_data(sensor_ip, test_com)
    if receive_data(sensor_ip, 'T'):
        print('test success')
        state = 1
    else:
        print ('%s test err'%sensor_ip)

#config_com = 'c' + chr(0) +chr(0) + chr(4)+chr(0) +chr(16) + chr(39)+chr(GAIN) +chr(0)
    config_com = 'c' + chr(0) +chr(0) + chr(4)+chr(0) +pack('<H', RATE).decode() +chr(GAIN) +chr(0)
    send_data(sensor_ip, config_com)
    if receive_data(sensor_ip, 'Co'):
        print('config success')
        state = state + 1
    else:
        print ('%s config fail'%sensor_ip)

    start_com  = 's' + ZERO + chr(1)+chr(0) + 't'
    if state == 2:
        send_data(sensor_ip, start_com)
        if receive_data(sensor_ip ,'St'): # it means it start to update data
            print("%s start upload data!"%sensor_ip)
        else:
            print( "%s can not start"%sensor_ip)

def sensor_stop(sensor_ip_list):

    stop_com  = 's' + chr(0)+chr(0)+ chr(1)+chr(0) + 'p'
    for ii in sensor_ip_list:
        send_data(ii, stop_com)
#print ("%s stoped"%ii)

def my_receive():

    print ("\n*****config information***** \nGain =  %d , record time = %d seconds \nstarted sensor are : %s \n**************************\n" % (GAIN, data_time, str(sensor_ip_list)))

    for ii in sensor_ip_list:
        sensor_config_start(ii, GAIN, RATE )

    start_time = get_time_tag()
    time.sleep(1)
    all_receive_data(sensor_ip_list, data_time)
    time.sleep(1)

    server_socket.close()
    finish_time = get_time_tag()
    #server_socket.recvfrom(1024) #Imi Fumei. The socket is already closed at this point.
    print(start_time)
    print(finish_time)


if __name__ == "__main__":

    my_receive()

    ss= input('wait')
