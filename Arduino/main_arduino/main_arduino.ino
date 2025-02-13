#define SAMPLING_PIN A0   // Pin to be sampled
#define BUFFER_LENGTH 200 // Number of samples for each data transfer

#define HANDSHAKE_START 0x7fff
#define HANDSHAKE_STOP 0x7ffe
#define MAX_TIME 10000

struct Buffer{
  int time[BUFFER_LENGTH] = {0};
  int data[BUFFER_LENGTH] = {0};
};
struct Buffer buffer;

bool is_buffer_ready_flag = false;


unsigned long time = 0;

void setup() {
  pinMode(SAMPLING_PIN, INPUT);
  Serial.begin( 115200 );

  cli();  // desactivation des interruptions

  // reinitialiser registre TCCR0A, TCCR0B et TCNT a 0
  TCCR0A = 0; 
  TCCR0B = 0; 
  TCNT0 = 0;   

  TCCR0A |= (1 << WGM01);               // timer en mode CTC (compter de 0 a la valeur contenue dans OCROA)
  TCCR0B |= (1 << CS01) | (1 << CS00);  // Set CS01 and CS00 bits for 64 prescaler
  TIMSK0 |= (1 << OCIE0A);              // Enable timer compare interrupt

  /* setter registre de comparaison pour interruption a 
   * toutes les 1ms => f = 1kHz
   * OCR0A = [ 16MHz / (64+1)(1kHz) ] -1 = 245
   */ 
  OCR0A = 245;

  sei();  // activation des interruptions
}

void loop() {
  static char tmp[32];
  if(is_buffer_ready_flag){
    sprintf(tmp, "%i,%i", HANDSHAKE_START, HANDSHAKE_START);
    Serial.println(tmp);
    //Serial.println(HANDSHAKE_START);

    for(int i=0; i<BUFFER_LENGTH; i++){
      sprintf(tmp, "%i,%i", buffer.time[i], buffer.data[i]);
      Serial.println( tmp );

      //Serial.println(buffer.time[i]);
      //Serial.println(buffer.data[i]);
    }

    sprintf(tmp, "%i,%i", HANDSHAKE_STOP, HANDSHAKE_STOP);
    Serial.println(tmp);
    //Serial.println(HANDSHAKE_STOP);

    is_buffer_ready_flag = false;
  }
}

ISR(TIMER0_COMPA_vect)
{
  static int sample_idx = 0;

  buffer.time[sample_idx] = time + sample_idx;
  buffer.data[sample_idx] = analogRead(SAMPLING_PIN);
  sample_idx++;

  if( sample_idx >= BUFFER_LENGTH ){
    sample_idx = 0;
    is_buffer_ready_flag = true;
  
    time += BUFFER_LENGTH;
    if( time >= MAX_TIME ){
      time = 0;
    }
  }
}

