#define SAMPLING_PIN A0   // Pin to be sampled
#define SAMPLING_RATE 10

int long pause = int( 1e3/10 );

void setup() {
  pinMode(SAMPLING_PIN, INPUT);
  Serial.begin( 115200 );
}

void loop() {
  static int val;
  static char to_send[16] = {0};

  val = analogRead(SAMPLING_PIN);
  sprintf( to_send, "%i\n", val );
  Serial.write(to_send);

  delay(pause);
}
