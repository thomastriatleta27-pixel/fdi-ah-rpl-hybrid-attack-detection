TIMEOUT(3600000, log.testOK());

while (true) {
  YIELD();

  log.append(
    "/home/joaorosa/contiki-ng/experimentos/final/logs/definitivo/normal/definitivo-normal-seed07-3600s.log",
    time + " ID:" + id + " " + msg + "\n"
  );
}
