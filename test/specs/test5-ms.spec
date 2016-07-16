# test inbound rules
# 2 participants - receiver has multiple router connections

mode multi-switch
participants 2
peers 1 2

#participant ID ASN PORT MAC IP PORT MAC IP
participant 1 100 PORT MAC 172.0.0.1/16 
participant 2 200 PORT MAC 172.0.0.11/16 PORT MAC 172.0.0.12/16 PORT MAC 172.0.0.13/16 PORT MAC 172.0.0.14/16 PORT MAC 172.0.0.15/16 PORT MAC 172.0.0.16/16 PORT MAC 172.0.0.17/16 PORT MAC 172.0.0.18/16 PORT MAC 172.0.0.19/16

host AS ROUTER _ IP           # host names of form a1_100 a1_110

announce 1 100.0.0.0/24 
announce 2 140.0.0.0/24 

flow b1 << 80
flow b2 << 81
flow b3 << 82
flow b4 << 83
flow b5 << 84
flow b6 << 85
flow b7 << 86
flow b8 << 87
flow b9 << 88

listener AUTOGEN 77 80 81 82 83 84 85 86 87 88

test init {
	listener
}

test regress {
	verify a1_100 b1_140 77
	verify a1_100 b1_140 80
	verify a1_100 b2_140 81
	verify a1_100 b3_140 82
	verify a1_100 b4_140 83
	verify a1_100 b5_140 84
	verify a1_100 b6_140 85
	verify a1_100 b7_140 86
	verify a1_100 b8_140 87
	verify a1_100 b9_140 88
}

test info {
	local ovs-ofctl dump-flows s1
	local ovs-ofctl dump-flows s2
	local ovs-ofctl dump-flows s3
	local ovs-ofctl dump-flows s4
}