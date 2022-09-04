setup:
	rm -rf blossom/static/
	poetry run python manage.py collectstatic --noinput --settings=blossom.settings.testing > /dev/null
	# poetry2setup is currently broken due to a deprecation in poetry. See https://github.com/abersheeran/poetry2setup/pull/1
	# poetry run poetry2setup > setup.py
	poetry run python -c "from pathlib import Path;from poetry.core.factory import Factory;from poetry.core.masonry.builders.sdist import SdistBuilder;print(SdistBuilder(Factory().create_poetry(Path('.').resolve())).build_setup().decode('utf8'))" > setup.py

build: setup shiv

clean:
	rm setup.py

shiv:
	mkdir -p build
	poetry run shiv -c blossom -o build/blossom.pyz . --compressed
