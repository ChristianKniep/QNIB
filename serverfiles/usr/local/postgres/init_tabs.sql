/* Nodetypes */
insert into nodetypes (nt_name) VALUES ('host');
insert into nodetypes (nt_name) VALUES ('switch');

/* Chassis */
insert into chassis (c_id,c_name) VALUES ('0','empty');

/* States */
INSERT INTO states (state_name) VALUES ('new');
INSERT INTO states (state_name) VALUES ('chk');
INSERT INTO states (state_name) VALUES ('ok');
INSERT INTO states (state_name) VALUES ('deg');
INSERT INTO states (state_name) VALUES ('nok');

/* perfkeys */
INSERT INTO perfkeys (pk_name) VALUES ('symbol_err_cnt');
INSERT INTO perfkeys (pk_name) VALUES ('link_downed');
INSERT INTO perfkeys (pk_name) VALUES ('rcv_err');
INSERT INTO perfkeys (pk_name) VALUES ('rcv_rem_phys_err');
INSERT INTO perfkeys (pk_name) VALUES ('rcv_switch_relay_err');
INSERT INTO perfkeys (pk_name) VALUES ('xmit_discards');
INSERT INTO perfkeys (pk_name) VALUES ('xmit_contraint_err');
INSERT INTO perfkeys (pk_name) VALUES ('rcv_constraint_err');
INSERT INTO perfkeys (pk_name) VALUES ('link_integrity');
INSERT INTO perfkeys (pk_name) VALUES ('buffer_overrun');
INSERT INTO perfkeys (pk_name) VALUES ('vl15_dropped');
INSERT INTO perfkeys (pk_name) VALUES ('xmit_pkts');
INSERT INTO perfkeys (pk_name) VALUES ('rcv_pkts');
INSERT INTO perfkeys (pk_name) VALUES ('xmit_data');
INSERT INTO perfkeys (pk_name) VALUES ('rcv_data');

