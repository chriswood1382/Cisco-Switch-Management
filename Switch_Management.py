#Loop through list of devices, navigate the cluster members if there, backup configuration, and update with new commands
#Created by Chris Wood
#Updated: 10/11/2016


#!/usr/bin/env python

import sys
import os
import socket
import netmiko

from netmiko import ConnectHandler


###########################################################################################################################
def show_version(ssh_conn):

    #run sho command on switch and assign string output to cluster_member 	
    version = ssh_conn.send_command("show version")
    
    #If statements to check if version string is included in the Show Version output. 
    #Assigns model number and sends it back to the main function. Prints banner to screen.
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

def find_command(switch_model):
      
    #Creates show command variable based on the switch model type and returns it to the main program.
    
    if switch_model == 'WS-C2960X' or switch_model == 'WS-C2960S' or switch_model == 'WS-C6509' or switch_model == 'WS-C3750X':
        
        command = ["interface gigabit 1/0/1", "description Right-Hand Rack"]                  
 
    
    if switch_model == 'WS-C2960' or switch_model == 'WS-C3560':
       
        command = ["interface fa0/1", "description Right-Hand Rack"]   

    
    if switch_model == 'WS-C4500X':
        
        command = "show interface status | inc notconnect"
       
    return command
    
###########################################################################################################################   
    
def send_command(ssh_conn, switch_model, host_name, command):

    member_dict = {}

    priv_list = ['privilege exec level 7 show running-config',
                 'privilege exec level 7 show cdp neighbor',
                 'privilege exec level 7 show cdp neighbor detail',
                 'privilege exec level 7 show lldp neighbor',
                 'privilege exec level 7 show  ip route',
                 'privilege exec level 7 show spanning-tree',
                 'privilege exec level 7 show mac address-table',
                 'privilege exec level 7 show ip interface',
                 'privilege exec level 7 show interface status']
                    
    pw_list = ['service password-encryption']                
    
    if switch_model == 'WS-C2960' or switch_model == 'WS-C3560' or switch_model == 'WS-C2960S':
               
        #run sho command on switch and assign string output to cluster_member 	
        cluster_member = ssh_conn.send_command("show cluster member")
        
        #Split output string by newline character into list variable
        members = cluster_member.split('\n')
       
        #Remove first three junk elements of the list
        del members[0:3]

        
        #Loop through every member in the list
        for member in members:
            
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
        
            print "Switch name is %s\n" % member_dict[key][0]

            write_config(ssh_conn, member_dict[key][0])
            
          
            ssh_conn.send_config_set(command)
            
            print ('\nCommand sent to Switch: %s' % (command))
            
            print(ssh_conn.send_command_expect('write memory'))
            
                                                       
        else:
            
            print "\n\nSwitch name is %s\n" % member_dict[key][0]
            
            #create client number command variable
            client_num = "rc " + str(key)

            #send command to traverse to member switch
            ssh_conn.send_command(client_num)
            
            #####Call model and show command functions again to check version against each switch in the cluster######
             
            switch_model = show_version(ssh_conn)
              
            write_config(ssh_conn, member_dict[key][0])
                       
            ssh_conn.send_config_set(command)
            print ('\nCommand sent to Switch: %s' % command)
           
            print(ssh_conn.send_command_expect('write memory'))
                     
            #Exit out of member switch
            ssh_conn.send_command("exit")

   
    return 
    
###########################################################################################################################
def interface_status(ssh_conn):

    int_dict = {}
          
    int_stat = ssh_conn.send_command("show interface status | inc notconnect")
    
    
    int_stat = int_stat.split('\n')

    for line in int_stat:
        
        if ('Te' in line) or ('Gi0/' in line) or ('Not Present' in line):
        
            del line
            
        elif ('hand' in line.lower()) or ('room' in line.lower()):
    
            port, name, stat, vlan, duplex, speed, type = line.split()
            
  
        else:
        
            port, stat, vlan, duplex, speed, type = line.split()
            
    return
                            
###########################################################################################################################
def write_config(ssh_conn, switch_name):
    
    path = 'I:\Technical Services\Data Communications\Python_Scripts\Switch_Config_Files'
    
    #Create filename from host name
    filename = switch_name.upper() + '_config.txt'
    
    filename = os.path.join(path, filename)

    config = ssh_conn.send_command("show configuration")  
    
    
    text_file = open(filename, "w")
    
    text_file.write(config)
    
    text_file.close()
    
    
    return
            

###########################################################################################################################
def disconnected_ports(ssh_conn):

    f = open('port_list.txt', "r")
    
    port = f.readline()
    
    while port:
           
        command = 'interface ' + port
               
        print command + '\n'
       
        version = ssh_conn.send_config_set(command)
        
        ssh_conn.send_command('authentication host-mode multi-auth')
        
        port = f.readline()
        
        
    ssh_conn.send_command_expect('write memory')
    

    config = ssh_conn.send_command_expect('sh conf')
    
    ssh_conn.send_command('exit')
   
    print config
    
    return
    
###########################################################################################################################

def main():
   
    print '''
    ***************************************************
    *                                                 *                
    *Send Commands to all switches in stack or cluster*
    *                                                 *
    ***************************************************
    
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

            
            ssh_conn = ConnectHandler(**switch_device)
          
            print('~'*85)
            print('Connecting to Switch: %s\n' % host_name)    
            
            
            #show = show_command(switch_model) 
            
            switch_model = show_version(ssh_conn)
            
            command = find_command(switch_model)
            
            send_command(ssh_conn, switch_model, host_name, command)
              
            ssh_conn.disconnect()
            
        except netmiko_exceptions as e:
            print('Failed to %s %s' % (host_name, e))
        
        host_name = f.readline().strip('\n')
        
        
    print '\n\n\n'
    print ('*'*100)
    print "End of script."
    print '\n\n\n'        

   

########################################################################################################################### 

if __name__ == "__main__":
    main()
    
    
    
    
    
    
    
    