while true;do
	gpioset gpiochip0 23=1
	sleep 0.0417
	gpioset gpiochip0 23=0
	sleep 0.0083
done
