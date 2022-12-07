function sleep(milliseconds) {
  const date = Date.now();
  let currentDate = null;
  do {
    currentDate = Date.now();
  } while (currentDate - date < milliseconds);
}

function goat() {
  var myAudio = new Audio("son.wav")
  sleep(1000)
  myAudio.play()
}


