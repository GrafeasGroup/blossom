setup:
	poetry run python manage.py collectstatic --noinput --settings=blossom.settings.testing > /dev/null
	poetry run poetry2setup > setup.py

build: setup shiv

clean:
	rm setup.py

shiv:
	mkdir -p build
	poetry run shiv -c blossom -o build/blossom.pyz . --compressed
