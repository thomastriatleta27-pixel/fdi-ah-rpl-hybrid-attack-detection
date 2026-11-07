TIMEOUT(3600000, log.testOK());

while (true) {
  YIELD();

  log.append(
    "/home/joaorosa/contiki-ng/experimentos/final/logs/definitivo/sinkhole/definitivo-sinkhole-seed06-3600s.log",
    time + " ID:" + id + " " + msg + "\n"
  );
}
