import lusee_script
import sys
routes = ['1234','2341','3412','4123']
gains = ["LLLL","MMMM", "HHHH"]

S = lusee_script.Scripter()




#S.add_route(2,3,1)
#S.write_script("test1")
#sys.exit(1)



S.add_reset()
S.add_ana_gain("LLLL")
S.add_start()
S.add_stop(10) ## 10 seconds

S.add_ana_gain("MMMM")
S.add_start()
S.add_stop(10) ## 10 seconds

S.add_ana_gain("HHHH")
S.add_start()
S.add_stop(10) ## 10 seconds


#for i in range(4):
#    S.add_route(i, None,None)
#S.add_ana_gain("MMMM")
#S.add_range_adc()



#for R in routes:
#    for i,r in enumerate(R):
##        S.add_route(i, int(r)-1)
#    for G in gains:
#        S.add_ana_gain(G)
#        S.add_range_adc()

#S.add_save("session_test1")
S.write_script("test1")
