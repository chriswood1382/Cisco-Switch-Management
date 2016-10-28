#Report device information from switch
#Created by Chris Wood
#Updated: 10/17/2016


#!/usr/bin/env python

import sys
import urllib2
import csv
import os
import paramiko
import netmiko

from getpass import getpass
from netmiko import ConnectHandler
from urllib2 import URLError

#Define dictionaries
member_dict = {}
mac_dict = {}
jack_dict = {}
ip_dict = {}
host_dict = {}

netmiko_exceptions = (netmiko.ssh_exception.NetMikoTimeoutException, 
                      netmiko.ssh_exception.NetMikoAuthenticationException)

#URL to pull vendor information about MAC Address
url = "http://api.macvendors.com/"

###########################################################################################################################
def show_version(ssh_conn):

    #run show command on switch to find switch model	
    version = ssh_conn.send_command("show version")
    
    #If statements to check if version string is included in the Show Version output. 
    
    if ("WS-C3560" in version) == True:
        
        model = "WS-C3560"
        
    elif ("WS-C4500X" in version) == True:
        
        model = "WS-C4500X"
        
    elif ("WS-C2960X" in version) == True:
        
        model = "WS-C2960X"

    elif ("WS-C2960S" in version) == True:
        
        model = "WS-C2960S"
   
    elif ("WS-C2960-" in version) == True:
        
        model = "WS-C2960"
       
    elif ("WS-C3750X" in version) == True:
        
        model = "WS-C3750X"
            
    elif ("WS-C6509" in version) == True:
        
        model = "WS-C6509"

    else:
         
        model = '<<<<<<<<<<No Switch Model Found>>>>>>>>>>'
        
    print "\nThe switch model is %s\n" % model

    return model
        
###########################################################################################################################

def show_command(switch_model):
      
    #Creates show command variable based on the switch model type and returns it to the main program.
    
    if (switch_model == 'WS-C2960X' or 
        switch_model == 'WS-C2960S' or 
        switch_model == 'WS-C6509' or 
        switch_model == 'WS-C3750X'):
        
        command = 'sh mac add | inc Gi'
 
    
    if switch_model == 'WS-C2960' or switch_model == 'WS-C3560':
       
        command = 'sh mac add | inc Fa'  

    
    if switch_model == 'WS-C4500X':
        
        command = 'sh mac add | inc Ten'
       
    return command
    
###########################################################################################################################   
    
def show_mac(ssh_conn, show, switch_model, host_name):

    member_dict = {}
    mac_dict = {}

    #Key variable for MAC dictionary
    index = 1
    
    if (switch_model == 'WS-C2960' or 
        switch_model == 'WS-C3560' or 
        switch_model == 'WS-C2960S'):
               
        #run sho command on switch and assign string output to cluster_member 	
        cluster_members = ssh_conn.send_command("show cluster member").split('\n')

        #Remove first three junk elements of the list
        del cluster_members[:3]

        
        #Loop through every member in the list
        for member in cluster_members:
            
            #Split each line into multiple variables
            num, mac, name, interface, var, var2, interface, state = member.split()
            
            #cleanup member name variable 
            name = host_name.upper() + '-' + str(num)
            
            
            #insert swith info into member_dict. Disregard all info but name and number
            member_dict[num] = (name, interface)
            
    ####Not sure why the string won't hold properly when I only have one entry in the dictionary. Without it returns the first char only###
    member_dict[0] = (host_name.upper(), 'dummy')
   
    
    #Loop through all cluster members sorted by the member number
    for key in sorted(member_dict.keys()):
    
    
        if key == 0:
        
            #send command to pull mac table for all Ports
            mac_table=ssh_conn.send_command(show)  

            write_config(ssh_conn, member_dict[key][0])
                                              
        else:
        
            #create client number command variable
            client_num = "rc " + str(key)

            #send command to traverse to member switch
            ssh_conn.send_command(client_num)
            
            ######Call model and show command functions again to check version against each switch in the cluster######
             
            switch_model = show_version(ssh_conn)
     
            show = show_command(switch_model) 
            
            write_config(ssh_conn, member_dict[key][0])

            #send command to pull mac table for all Ports
            mac_table=ssh_conn.send_command(show)
                     
            #Exit out of member switch
            ssh_conn.send_command("exit")
            
                
        #Split output string by newline character into list variable
        mac_table = mac_table.split('\n')
        
        #Print message if no mac addresses are read from switch
        if mac_table[0] == '':
            
            print "\n\n\nThere are no MAC addresses found on " + member_dict[key][0] + '\n\n\n'
        
        else:
        
            #Loop through every member in the list
            for line in mac_table:
                
                if (('0/49' in line) == True or 
                    ('0/50' in line) == True or 
                    ('0/51' in line) == True or 
                    ('0/52' in line) == True or 
                    ('Gi0/' in line) == True):
                    
                    del line
                
                else:
                                                 
                    #Split mac table into different string variables
                    vlan, mac_add, type, port = line.split()
                 
                    #pull down vendor information based on mac address
                    try:
                        vendor = urllib2.urlopen(url+mac_add).read()
                     
                    except urllib2.HTTPError, e:
                        vendor = 'No Vendor Found -- HTTP Error = ' + str(e.code)
                     
                    #Compile all variables into dictionary
                    mac_dict[index] = (member_dict[key][0], 
                                       switch_model, 
                                       port, 
                                       vlan, 
                                       mac_add, 
                                       vendor)
                        
                    #Print info to screen          
                    print "Switch: %s, Port: %s, VLAN: %s, MAC: %s Vendor: %s " % (mac_dict[index][0], 
                                                                                   mac_dict[index][2], 
                                                                                   mac_dict[index][3], 
                                                                                   mac_dict[index][4], 
                                                                                   mac_dict[index][5])
                    
                    #increment index for key variable in dictionary
                    index = index + 1     
   
    return mac_dict
    
########################################################################################################################### 
def calc_jack (ssh_conn, mac_dict, host_name):

    jack_dict = {}   

    #run show command to report all description lines
    description = ssh_conn.send_command('show conf | inc description')
    
    #Search against Right or Left in the description field. If one of the terms in present configure the lookup file
    if ('right hand' in description.lower()) or ('right-hand' in description.lower()):
        
        filename = 'Right_hand_rack.txt'

    if ('left hand' in description.lower()) or ('left-hand' in description.lower()):
    
        filename = 'Left_hand_rack.txt'
        
    #Loop through all entries in mac_dict        
    for key in mac_dict:
    
        #Lookup switch stack or cluster number. If 2960X subtract 1 to match to lookup text file
        if mac_dict[key][1] == 'WS-C2960X':
            
            switch_num = int(mac_dict[key][2][2]) - 1
                        
        else:
            
            if '-' in mac_dict[key][0]:
            
                switch_num = int(mac_dict[key][0][-1])
                
            else:
            
                switch_num = 0
        
        #carve out specific port number 
        port = mac_dict[key][2][-2:].strip('/')
            
        #Rack number within a TR is always the last number in the host name
        rack = host_name[-1]
                
        #combine switch number with port into location to be used to look up against text file.
        location = str(switch_num) + '-' + str(port)
    
        #If configuration does not contain any description fields, return as Unknown
        if description == '':
        
            jack = "Unknown Jack"
    
        #If descrtiption contains the keywords we are looking for continue
        elif ('left' in description.lower()) or ('right' in description.lower()):
                     
            #Jack lookup can only work against the 'A' side switches this means only the first 4 in a given stack or cluster numbered 0-3         
            if (switch_num < 4) and (rack != 'B'):
            
                #Open lookup file and if search line by line for location variable. If found return the line and split it out to have jack variable
                with open(filename) as f:
                    
                    for line in f:
                        
                        if location in line:
                            
                            temp, jack = line.split()
                                
                
                #These are the exceptions to the standard jack numbering scheme where some TRs start with 200 or 300 instead of from 1
                if (host_name[2:5] == '235' or 
                    host_name[2:5] == '252' or 
                    host_name[2:5] == '321' or 
                    host_name[2:5] == '521' or 
                    host_name[2:5] == '631'):
                
                    jack = int(jack) + 200
                    
                elif host_name[2:5] == '341':
                
                    jack = int(jack) + 300
                    
                
                #If switch is in the second or third rack in a TR we have to calculate for the ports on the first racks
                if int(rack) == 2:
                
                    jack = int(jack) + 192

                elif int(rack) == 3:
                
                    jack = int(jack) + 384
                
        
                #Full jack number has to be a set length of numbers. If jack number is below 100 we have to add zeros 
                if len(str(jack)) == 1:
                    
                    jack = '00' + str(jack)
                
                if len(str(jack)) == 2:
                    
                    jack = '0' + str(jack)
                
                
                if   'H' == host_name[2].upper():
                
                    jack = '30' + host_name[3:5] + str(jack) + 'A'
                
                elif 'OS' == host_name[2:3].upper():
                
                    jack = '18' + host_name[4] + str(jack) + 'A'
                    
                else:    
                    
                    #combine final jack name using part of hostname 
                    jack = host_name[2:5] + str(jack) + 'A'   
                
            #Anything not on the A side switches cannot be known.     
            else:            
            
                jack = "Unknown B Side Jack"
                        
        else:
        
            jack = "Unknown Jack"
             
        #Assemble all data into new dictionary and return it      
        jack_dict[key] = (mac_dict[key][0], 
                          mac_dict[key][1], 
                          mac_dict[key][2], 
                          jack, 
                          mac_dict[key][3], 
                          mac_dict[key][4], 
                          mac_dict[key][5])
    
    return jack_dict
 
###########################################################################################################################
def find_router(ssh_conn):
    
    #pull default gateway information from config, set this as the router for the switch, and then return router IP

    show_conf=ssh_conn.send_command('show conf | inc ip default-gateway') 

    temp1, temp2, router = show_conf.split()
     
   
    print '\nThe router is: %s\n\n' % router
         
    return router    
    
###########################################################################################################################
def show_ip (ssh_router, jack_dict):
    
    ip_dict = {}
    
    
    #iterate through the dictionary file passed from the main program
    for key in jack_dict:
        
        #create show command based on mac address from dictionary
        show = "show ip arp " + jack_dict[key][5]
        
        print show
        
        arp_entry=ssh_router.send_command(show)

        #for null entries assign string for ip
        if arp_entry == '' or ('Ambiguous command' in arp_entry):
            
            ip_addr = 'No IP Address Found'   
            
        else:
    
            arp_entry = arp_entry.split('\n')
           
            #Remove first three junk elements of the list
            del arp_entry[:1]
             
            protocol, ip_addr, age, mac, type, interface  = arp_entry[0].split()
        
        print '\n %s \n' % ip_addr
        
        #create new dictionary based off of device IP address and the other variables from mac_dict
        ip_dict[key] = (jack_dict[key][0], 
                        jack_dict[key][1], 
                        jack_dict[key][2], 
                        jack_dict[key][3], 
                        jack_dict[key][4], 
                        jack_dict[key][5], 
                        ip_addr, 
                        jack_dict[key][6]) 
        
    ssh_router.send_command("exit")
         
    return ip_dict
    
###########################################################################################################################

def show_host(ip_dict, user_name_dns, my_pass_dns):
    
    host_dict = {}
    
    print ('#'*85)
    print '\n\nCONNECTING TO DNS SERVER\n'
    print ('#'*85)
   
    dns_server = 'alfred'

    #Need to use paramiko to connect to the linux DNS server
    ssh_dns = paramiko.SSHClient()
    
    #use this line to avoid issues with ssh keys
    ssh_dns.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    ssh_dns.connect(dns_server, username= user_name_dns, password= my_pass_dns)
    
    for key in ip_dict:
        
        #if we didn't know the IP address from previous function, skip process to try and lookup hostname
        if ip_dict[key][6] == 'No IP Address Found':

            hostname = 'No Hostname Found'
        
        else:
                
            #create NSlookup command for each IP in the dictionary
            show = "nslookup " + ip_dict[key][6]
            
            #print show to screen to validate data while watching program run
            print '\n' + show + '\n'
            
            #standard paramiko method for pulling in data from command
            stdin, stdout, stderr = ssh_dns.exec_command(show)

            #read in stdout to string variable
            host_entry = stdout.read()
            
            
            if "server can't find" in host_entry:
            
                hostname = 'No Hostname Found'
                  
            else:
            
                host_entry = host_entry.split('\n')
               
                #Remove first three junk elements of the list
                del host_entry[:3]
                
                ip, name, temp, hostname = host_entry[0].split()
                
                #cleanup period at the end of the string
                hostname = hostname[:-1]
           
            print hostname
            
        #create another dictionary using hostname and variables from ip_dict     
        host_dict[key] = (ip_dict[key][0], 
                          ip_dict[key][1], 
                          ip_dict[key][2], 
                          ip_dict[key][3], 
                          ip_dict[key][4], 
                          ip_dict[key][5], 
                          ip_dict[key][6], 
                          hostname, 
                          ip_dict[key][7]) 

    #close ssh connection to DNS server
    ssh_dns.close()
    
    return host_dict  

###########################################################################################################################
def write_config(ssh_conn, switch_name):

    path = 'I:\Technical Services\Data Communications\Python_Scripts\Switch_Config_Files'
    
    #Create filename from host name
    filename = switch_name.upper() + '_config.txt'
    
    filename = os.path.join(path, filename)

    config = ssh_conn.send_command("show configuration").split('\n')
    
    del config[:1]
    
    config = '\n'.join(config)
   
    text_file = open(filename, "w")
    
    text_file.write(config)
    
    text_file.close()
    
    
    return
    
###########################################################################################################################
def write_dict(host_name, host_dict):

    path = 'I:\Technical Services\Data Communications\Python_Scripts\Switch_Report_Output'
    
    #Create filename from host name
    filename = host_name.upper() + '_HostList.csv'
    
    filename = os.path.join(path, filename)
    
    try:
        with open(filename, 'wb') as file:
            writer = csv.writer(file)   
            #Create header for csv file
            writer.writerow(["Switch_Name", 
                             "Switch_Model", 
                             "Port", 
                             "Jack", 
                             "VLAN", 
                             "MAC_Address", 
                             "IP_Address", 
                             "Host_Name", 
                             "Vendor_Name"])
                                     
            #Write all values in the dictionary
            for data in host_dict:
                writer.writerow(host_dict[data])
                
    except IOError as (errno, strerror):
        print ("I/O error({0}): {1}".format(errno, strerror))
        
        
    return path
    
###########################################################################################################################

def main():
   
    print '''
    ****************************************
    *                                      *                
    *       Connect to Switch via SSH      *
    *Report all devices currently connected*
    *                                      *
    ****************************************
    
    '''

    #Prompt user for switch name and logon credentials
    #host_name = raw_input("Enter Switch Name: ")
    user_name_sw = raw_input("Enter User Name for Switches/Routers: ")
    my_pass_sw = getpass()

    user_name_dns = raw_input("\n\nEnter User Name for DNS Server: ")
    my_pass_dns = getpass()
    
    #open switch inventory file
    f = open('Switch_Inventory_temp.txt', "r")
    
    host_name = f.readline().strip('\n')
    
    while host_name:
        
        try:
        
            #Compile SSH connection data using netmiko
            switch_device = {
                'device_type': 'cisco_ios',
                'ip': host_name,
                'username': user_name_sw,
                'password': my_pass_sw,
                'secret': my_pass_sw,
                'port': 22,
            }

            #Connect to switch with SSH information
            ssh_conn = ConnectHandler(**switch_device)
            
            print('\n\n\n')
            print('~'*85)
            print('Connecting to Switch: %s\n' % host_name) 
            
            #call functions
            switch_model = show_version(ssh_conn)
            
            show = show_command(switch_model) 
            
            mac_dict = show_mac(ssh_conn, show, switch_model, host_name)
            
            jack_dict = calc_jack(ssh_conn, mac_dict, host_name)
        
            router = find_router(ssh_conn)
            
            #Disconnect from switch SSH Connection
            ssh_conn.disconnect()
            
            
            try:
                #create new SSH connection for router
                router_device = {
                    'device_type': 'cisco_ios',
                    'ip': router,
                    'username': user_name_sw,
                    'password': my_pass_sw,
                    'secret': my_pass_sw,
                    'port': 22,
                }            
                  
                #Connect to router with SSH information
                ssh_router = ConnectHandler(**router_device)      

                #call functions
                ip_dict = show_ip(ssh_router, jack_dict)
   
                host_dict = show_host(ip_dict, user_name_dns, my_pass_dns)
                
                path = write_dict(host_name, host_dict)
        
            except netmiko_exceptions as e:
        
                print('Failed to Router: %s %s' % (router, e))

        except netmiko_exceptions as e:
        
            print('Failed to Switch: %s %s' % (host_name, e))

        host_name = f.readline().strip('\n')
  
  
    print '\n\n\n'
    print ('*'*100)
    print "End of Report. See Output Files in: %s\n\n\n" % path
   
########################################################################################################################### 

if __name__ == "__main__":
    main()
    
    
    
