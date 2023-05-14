###CO2 in the Classroom###
#     Matthew Starkie    #
#   Updated 17/03/2023   #
##########################

#import required components
from machine import ADC, Pin, UART #LEDS and sensair sensor
import time #Used to enable time delays
import urequests as requests #Used to enable the get method of reporting to the SQL database
import network #Used to enable connection to the internet
import micropython #System functions
import rp2 #pi pico functions
import ubinascii #Used to decode the devices mac address

#configure hardware address
wlan = network.WLAN(network.STA_IF)
uart0 = machine.UART(0, 9600, tx=Pin(0), rx=Pin(1), bits=8, parity=None, stop=1)
Green = machine.Pin(10,machine.Pin.OUT)
Yellow = machine.Pin(11,machine.Pin.OUT)
Red = machine.Pin(12,machine.Pin.OUT)

#WiFi Settings
ssid = 'HPSWiFi'
password = 'indigo23'

#Monitor Indetification
monitorID = 'MON_101'
authCode = 'JBLLCYVA'

####################



#Function - initialise - start up lights sequence - Green > Yellow > Red
def initialise():
    leds(0,0,1)
    time.sleep(0.5)
    leds(0,1,0)
    time.sleep(0.5)
    leds(1,0,0)
    time.sleep(0.5)
    leds(0,0,0)
    time.sleep(0.5)
    
# Function - ledsflash
# red,yellow,green - either 0 or 1. If a colour is set as 1, it will be included in the flash routine.
# repeat - integer. Decides how many times the flashing sequence will repeat.
# function uses a try loop. In the event of a failure a event report is sent to the SQL database and the hardware is reset.
def ledsflash(red,yellow,green,repeat):
    try:
        x = 0
    
        while x < repeat :
            if red == 1:
                leds(1,0,0)
                
            if yellow == 1:
                leds(0,1,0)
                
            if green == 1:
                leds(0,0,1)
        
            time.sleep(0.5)    
            leds(0,0,0)
            time.sleep(0.5)  
            x = x+1
    except:
        eventreport('5','LED_Fail')
        machine.reset()
        
# Function - leds
# red,yellow,green - either 0 or 1. If a colour is set as 1, it will be activated.
# function uses a try loop. In the event of a failure a event report is sent to the SQL database and the hardware is reset.
def leds(red,yellow,green):
    try:
        if red == 1:
            Red.on()
        else :
            Red.off()
            
        if yellow == 1 :
            Yellow.on()
        else :
            Yellow.off()
            
        if green == 1 :
            Green.on()
        else :
            Green.off()
    except:
        eventreport('5','LED_Fail')
        machine.reset()

# Function - eventreport
# Used to report an event to the SQL database using the GET method.
# eventid - string
# info - string
# function uses a try loop. If a failure occurs or a status code of anything other than 200 is received then the machine pauses for 60 seconds and then a hardward reset occurs.
def eventreport(eventid,info):
    try:
        url = 'https://co2intheclassroom.co.uk/mon/eventreport.php?auth='+authCode+'&monid='+monitorID+'&eventid='+eventid+'&eventinfo='+info
        r = requests.get(url)
        
        if r.status_code != 200 :
            time.sleep(60)
            machine.reset()
                
        r.close()
        
    except:
        machine.reset()    

# Function - connect
# Used to connect the pico to a wireless network
# ssid - string - this value is set above in the monitor configuration
# password - string - this value is set above in the monitor configuration
def connect(ssid,password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True) #wirless is activated

    attempts = 0 #attempts set to 0
    
    #try loop - if a failure occurs at any point then the hardware device is reset
    try:
        #loop will try to connect to wifi 120 times. Waiting 3 seconds between each attempt.
        while wlan.isconnected() == False:
            if attempts < 120 :
                ledsflash(1,0,0,2) # the RED led will flash to indicate that the monitor is trying to connect
                wlan.connect(ssid, password)
                time.sleep(3)
                attempts = attempts + 1
            else : #if after 120 attempts the monitor has been unable to connect the hardware is reset completely
                wlan.disconnect()
                machine.reset()
        
        #Code from here is run if the connection is successful
        ledsflash(0,0,1,2) #Green LED flashes 2 times
        
        mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode() #the devices mac address is decoded and stored in the variable 'mac'
        ip = wlan.ifconfig()[0] #the ip address of the device is stored in the variable 'ip'
        
        #The ip, mac and 'Boot_Up' are submitted to the SQL database using the eventreport function.
        eventreport('1',ip)
        eventreport('2',mac)
        eventreport('3','Boot_Up')
        
        leds(1,1,1) # all LEDs are turned on to indicate that the device is now connected. Once the reading loop occurs these are all turned off
    
    except:
        machine.reset()

#function readco2
#This function is used to communicate with the Sensair S8 sensor using UART. This function has no inputs and returns a value (as a number)
def readco2():
    #uses a try loop. In the event of a failure a "Sensor_Fail" event is sent the SQL database and the machine is reset.
    try:
        uart0.flush() # clear UART cache - used as a precation to prevent a false first reading.
        
        time.sleep(0.5) # wait for 0.5 seconds
        uart0.write(b'\xFE\x44\x00\x08\x02\x9F\x25') #Command to request the CO2 reading sent to the sensor
        time.sleep(0.5) # wait for 0.5 seconds
        
        result = uart0.read(7) # the response from the sensair is stored in the variable 'result'. The result is a hexadecimal
        
        #converts the hexadecimal response in to a number
        high=result[3] 
        low=result[4]
        co2 = (high*256) + low
        
        uart0.flush() #clear UART cache. This to keep device storage levels to a minimum.
        
        return(co2) #return the CO2 reading as a number
    
    except:
        eventreport('4','Sensor_Fail')
        machine.reset()

#function submitreading
# Used to report an co2 reading to the SQL database using the GET method.
# co2 - number
def submitreading(co2):
    # function uses a try loop. If a failure occurs or a status code of anything other than 200 is received then the machine pauses for 60 seconds and then a hardward reset occurs.
    try: 
        co2s = str(co2) #co2 reading is converted to a string and stored in the variable 'co2s'
        
        r = requests.get(url = 'https://co2intheclassroom.co.uk/mon/readingsubmit.php?auth='+authCode+'&monid='+monitorID+'&val='+co2s)
        
        if r.status_code != 200 :
            time.sleep(60)
            machine.reset()
            
        r.close()
    except:
        machine.reset()

#function readingcheck
# reading = number
# Function takes in a co2 reading and first flashes all LEDs 3 times to indicate a new reading has been taken.
def readingcheck(reading):
    #try loop is used. If a failure occurs the hardward is reset.
    try:
        ledsflash(1,1,1,3)     
        
        #if the reading is less than 1000 then the green led is enabled
        if reading < 1000 :
            leds(0,0,1)
        
        #if the reading is between 1000 and 1500 then the yellow led is enabled
        if reading in range (1000,1500) :
            leds(0,1,0)
            
        #if the reading is greater than 1501 then the red led is enabled
        if reading > 1501 :
            leds(1,0,0)
            
    except:
        machine.reset()
#function main
#This the core function which loops continuosuly to enable the monitor to function.
def main():
    #on first load the initialise function is loaded. This turns each led on individually
    initialise()
    
    #readings count is set to 0
    readingcount = 0
    
    try:
        #core loop - try loop is used. If a failure occurs at any point then the hardware will reset
        while True :
            #Check that the pico is still connected to the wifi
            if wlan.isconnected() == True:                
                #If the system has already carried out 2 readings#
                if readingcount > 2 :
                    leds(0,0,0) # turn all leads off
                    co2 = readco2() # read the current co2 level
                    readingcheck(co2) #set the leds depending on the result
                    submitreading(co2) #send the reading to the SQL database
                ##################################################   
                readingcount = readingcount + 1 # add 1 to the reading count
                time.sleep(120) #pause for 120 seconds
            
            #If the pico is no longer connected to wifi
            else:
                time.sleep(10) #sleep for 10 seconds to give the device/internet connection a little time
                connect(ssid,password) #connect to the wifi 
    except:
            machine.reset()
    
main() #loads the main function

