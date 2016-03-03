# -*- coding: utf-8 -*
from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app
from flask.ext.login import login_required, current_user
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, QuestionForm, AnswerForm, CommentForm,\
    ChangePassWordForm, ChangeEmailForm
from .. import db
from ..models import Permission, Role, User, Question, Answer, Comment
from ..decorators import admin_required,  permission_required


@main.route('/', methods=['GET', 'POST'])
def index():
    page = request.args.get('page', 1, type=int)
    pagination = Question.query.order_by(Question.timestamp.desc()).paginate(
        page, per_page=current_app.config['INDEX_QUESTIONS_PER_PAGE'],
        error_out=False)
    questions = pagination.items
    return render_template('index.html', questions=questions,
                           pagination=pagination)

@main.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST' :
        keyword = "%" + request.form['search'] + "%"
        if keyword in "%%":
                return render_template("search.html")
        page = request.args.get('page', 1, type=int)
        pagination = Question.query.filter(Question.title.like(keyword)).order_by(Question.timestamp.desc()).paginate(
            page, per_page=current_app.config['INDEX_QUESTIONS_PER_PAGE'],
            error_out=False)
        questions = pagination.items
        return render_template("search.html", questions=questions, pagination=pagination, keyword=keyword[1:-1])
    return render_template("search.html")
        
@main.route('/test', methods=['GET', 'POST'])
def test():
    return render_template("test.html")


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    flash('You are now following %s.' % username)
    return redirect(url_for('.user', username=username))
    

@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    flash('You are not following %s anymore.' % username)
    return redirect(url_for('.user', username=username))

@main.route('/setting/<navtab>', methods=['GET', 'POST'])
@main.route('/setting', methods=['GET', 'POST'])
@login_required
def setting(navtab='profile'):
    passwdForm = ChangePassWordForm()
    emailForm  = ChangeEmailForm()
    if emailForm.validate_on_submit():
        current_user.email = emailForm.email.data
        db.session.add(current_user)
        flash("your email has been updated")
        return redirect(url_for('.user', username=current_user.username))
    if passwdForm.validate_on_submit():
        if current_user.verify_password(passwdForm.old_password.data):
            current_user.password = passwdForm.password.data
            db.session.add(current_user)
            flash("your password has been updated")
            return redirect(url_for('.user', username=current_user.username))
        else:
            flash("invalid password")
        
    return render_template("setting.html", passwdForm=passwdForm, emailForm=emailForm)


@main.route('/user/<username>', methods=['GET', 'POST'])
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    askpagination = Question.query.filter_by(author_id=user.id).order_by(Question.timestamp.desc()).paginate(
        page, per_page=current_app.config['PROFILE_QUESTIONS_PER_PAGE'],
        error_out=False)
    questions = askpagination.items
    page = request.args.get('page', 1, type=int)
    anspagination = Answer.query.filter_by(author_id=user.id).order_by(Answer.timestamp.desc()).paginate(
        page, per_page=current_app.config['PROFILE_QUESTIONS_PER_PAGE'],
        error_out=False)
    questions = askpagination.items
    answers = anspagination.items
    return render_template('user.html', user=user, questions=questions, answers=answers,
                           askpagination=askpagination, anspagination=anspagination)

@main.route('/ask', methods=['GET', 'POST'])
@login_required
def ask():
    form = QuestionForm()
    if current_user.can(Permission.WRITE_ARTICLES) and \
            form.validate_on_submit():
        question = Question(body=form.body.data,
                            title = form.title.data,         
                    author=current_user._get_current_object())
        db.session.add(question)
        db.session.commit()
        """ only insert data to sql table can trigger the action to generate an unique ID"""
        id = Question.query.filter_by(title=question.title).order_by(Question.timestamp.desc()).first().id
        return redirect(url_for('.question', id=id))
    return render_template("ask.html", form=form)


@main.route('/answer/<int:id>', methods=['GET', 'POST'])
@login_required
def answer(id):
    """show the answer"""
    answer = Answer.query.filter_by(id=id).first_or_404()
    return render_template("answer.html", answer=answer)

@main.route('/question/<int:id>', methods=['GET', 'POST'])
@login_required
def question(id):
    """show the questions"""
    answerForm = AnswerForm()
    commentForm = CommentForm()
    question = Question.query.filter_by(id=id).first_or_404()
    answer_id =  request.args.get('answer_id', -1, type=int)
    comments = Comment.query.filter_by(answer_id=answer_id).order_by(Comment.timestamp.desc())
    answer= Answer.query.filter_by(id=answer_id)
    if current_user.can(Permission.WRITE_ARTICLES) and \
       answerForm.validate_on_submit():
                answer = Answer(answer=answerForm.body.data,
                                 author=current_user._get_current_object(),
                                 authorname=current_user.username,
                                 question=question )
                db.session.add(answer)
                return redirect(url_for('.question', id=id))

    if current_user.can(Permission.WRITE_ARTICLES) and \
       commentForm.validate_on_submit():
                comment = Comment(comment=commentForm.body.data,
                                 author=current_user._get_current_object(),
                                 authorname=current_user.username,
                                 answer=answer)
                db.session.add(answer)
                return redirect(url_for('.question', id=id))

    answers = Answer.query.filter_by(question_id=question.id).order_by(Answer.timestamp.desc())            
    asker = User.query.filter_by(id=question.author_id).first()
    return render_template("question.html", question=question, asker=asker,
                           answerForm=answerForm, answers=answers, comments=comments,
                           commentForm=commentForm, answer_id=answer_id)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)
