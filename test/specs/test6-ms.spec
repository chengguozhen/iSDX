mode multi-switch
participants 3
peers 1 2 3

participant 1 100 PORT MAC 172.0.0.10/16
participant 2 200 PORT MAC 172.0.0.20/16
participant 3 300 PORT MAC 172.0.0.30/16

host AS ROUTER _ IP           # host names of form a1_100 a1_110

announce 1 110.0.0.0/24 140.0.0.0/24 150.0.0.0/24
announce 2 120.0.0.0/24 150.0.0.0/24 160.0.0.0/24
announce 3 130.0.0.0/24 160.0.0.0/24 140.0.0.0/24

flow a1 80 >> b
flow b1 80 >> c
flow c1 80 >> a
flow a1 81 >> c
flow b1 81 >> a
flow c1 81 >> b

listener AUTOGEN 80 81 88

test init {
	listener
}

test regress {
	verify a1_110 b1_160 80
	verify b1_120 c1_140 80
	verify c1_130 a1_150 80
	
	verify a1_110 c1_160 81
	verify b1_120 a1_140 81
	verify c1_130 b1_150 81
	
	verify a1_110 b1_160 88
	verify b1_120 a1_140 88
	verify c1_130 a1_150 88
}

test info {
	local ovs-ofctl dump-flows s1
	local ovs-ofctl dump-flows s2
	local ovs-ofctl dump-flows s3
	local ovs-ofctl dump-flows s4
}
