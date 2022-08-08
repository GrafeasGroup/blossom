setup:
	python manage.py collectstatic --noinput > /dev/null
	poetry2setup > setup.py

build: setup shiv

clean:
	rm setup.py

shiv:
	mkdir -p build
	shiv -c blossom -o build/blossom.pyz . --compressed
