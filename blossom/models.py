from blossom.authentication.custom_user import BlossomUser

# This is only here because Django hates recognizing the AUTH_USER_MODEL when
# it's in a subdirectory. If you want to do any edits to the user model, make
# them in the authentication folder.