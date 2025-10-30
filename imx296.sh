while true;do
	gpioset gpiochip0 23=1
	sleep 1.9999
	gpioset gpiochip0 23=0
	sleep 0.0033
done
