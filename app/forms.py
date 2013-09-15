from flask_wtf import Form, TextField, BooleanField, Required, TextAreaField


class LoginForm(Form):
    openid = TextField('openid', validators=[Required()])
    remember_me = BooleanField('remember_me', default=False)


class ProjectForm(Form):
    projName = TextField('name', validators=[Required()])


class NewPost(Form):
    newPostTitle = TextField('postTitle', validators=[Required()])
    newPostContent = TextAreaField('Content', id="content-area", validators=[Required()])


# class UploadForm(Form):
#     upload = FileField("Upload your image",
#                validators=[file_required(), file_allowed(images, "Images only!")])
