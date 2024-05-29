import lusee_script

routes = ['1234','2341','3412','4123']
gains = ["LLLL","MMMM", "HHHH"]

S = lusee_script.Scripter()

S.add_reset()
for R in routes:
    for i,r in enumerate(R):
        S.add_route(i, int(r))
    for G in gains:
        S.add_ana_gain(G)
        S.add_range_adc()

S.add_save("session_test1")
S.write_script("test1")