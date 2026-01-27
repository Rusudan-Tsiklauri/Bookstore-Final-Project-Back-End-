from flask import render_template, redirect, flash
from flask_wtf import form
from werkzeug.security import generate_password_hash,check_password_hash
from forms import SignupForm, ProductForm, LoginForm, OrderForm, AuthorForm, ChangePasswordForm
from models import Product, Comment, User, Order,Author,Review
from ext import app, db
from flask_login import login_user, logout_user, login_required, current_user
from flask import session,request
import os

profiles = []
products = []

def get_cart_items():
    return session.get('cart', [])



@app.route("/")
def home():
    role = "user"
    cart_items = len(get_cart_items())
    return render_template("index.html", products=Product.query.all(), role=role, cart_items=cart_items)




@app.route("/signup", methods=["POST", "GET"])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data


        if  User.query.filter_by(username=username).first():
            flash("იუზერნეიმი უკვე არსებობს, გთხოვთ შექმნათ ახალი იუზერნეიმი","danger")

        else:
            new_user = User(username=username, password=password)

            db.session.add(new_user)
            db.session.commit()

            flash("თქვენ წარმატებით დარეგისტრირდით,  გაიარეთ ავტორიზაცია", "success")
            return redirect("/login")

    return render_template("SignUp.html", form=form)



@app.route("/login", methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(form.username.data == User.username).first()
        if user and user.check_password(form.password.data):
            login_user(user)

            flash("თქვენ წარმატებით გაიარეთ ავტორიზაცია", "success")
            return redirect("/")
        else:
            flash("თქვენს მიერ შეყვანილი პაროლი ან იუზერნეიმი არასწორია", "danger")


    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    logout_user()
    flash("თქვენ წარმატებით გამოხვედით სისტემიდან", "success")
    return redirect("/")


@app.route("/create_product", methods=["GET", "POST"])
@login_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        new_product = Product(name=form.name.data, price=form.price.data, author=form.author.data, genre=form.genre.data, description=form.description.data)
        db.session.add(new_product)

        image = form.image.data
        img_location = os.path.join(app.root_path, "static", "images", image.filename)
        image.save(img_location)

        new_product.image = image.filename

        db.session.add(new_product)
        db.session.commit()

        flash("პროდუქტი წარმატებით დაემატა", "success")
        return redirect("/")

    return render_template("create_product.html", form=form)


@app.route("/edit_product/<int:product_id>", methods=["POST", "GET"])
@login_required
def edit_product(product_id):
    product = Product.query.get(product_id)
    form = ProductForm(name=product.name, price=product.price, author=product.author, genre=product.genre, description=product.description)
    if form.validate_on_submit():
        product.name = form.name.data
        product.price = form.price.data
        product.author = form.author.data
        product.genre = form.genre.data
        product.description = form.description.data

        if form.image.data:
            image_file = form.image.data
            filename = image_file.filename
            image_file.save(f"static/images/{filename}")
            product.image = filename

        db.session.commit()

        flash("პროდუქტი წარმატებით განახლდა!", "success")
        return redirect("/")

    return render_template("create_product.html", form=form)


@app.route("/delete/<int:product_id>")
@login_required
def delete(product_id):
    product = Product.query.get(product_id)

    db.session.delete(product)
    db.session.commit()

    flash("პროდუქტი წარმატებით წაიშალა", "danger")
    return redirect("/")


@app.route("/detailed/<int:product_id>")
def detailed(product_id):
    product = Product.query.get(product_id)
    comments = Comment.query.filter(Comment.product_id == product_id)
    return render_template("detailed.html", product=product, comments=comments)


@app.route("/genre/<genre_name>")
def show_genre(genre_name):
    genre_products = Product.query.filter_by(genre=genre_name).all()
    return render_template("genre_page.html", products=genre_products, genre=genre_name)


@app.route("/about_us")
def about():
    return render_template("about_us.html")


@app.route("/cart")
def cart():
    cart_product_ids = get_cart_items()
    length = len(cart_product_ids)
    if cart_product_ids:
        products = Product.query.filter(Product.id.in_(cart_product_ids)).all()
    else:
        products = []
    return render_template('Cart.html', products=products, cart_items=length)


@app.route('/add_to_cart/<int:item_id>', methods=['GET', 'POST'])
def add_to_cart(item_id):
    if not current_user.is_authenticated:
        flash("კალათაში დასამატებლად გთხოვთ ჯერ გაიაროთ ავტორიზაცია", "warning")
        return redirect("/login")
    cart = session.get('cart', [])
    cart.append(item_id)

    session['cart'] = cart
    return redirect("/")


@app.route('/remove_from_cart/<int:item_id>')
def remove_from_cart(item_id):
    cart = session.get('cart', [])
    if item_id in cart:
        cart.remove(item_id)
        session['cart'] = cart


    flash("პროდუქტი კალათიდან წარმატებით წაიშალა","success")
    return redirect("/cart")


@app.route("/checkout")
def checkout():
    form = OrderForm()
    cart_ids = get_cart_items()
    if not cart_ids:
        flash("თქვენი კალათა ცარიელია", "danger")
        return redirect("/")


    actual_products = Product.query.filter(Product.id.in_(cart_ids)).all()
    total = sum(product.price for product in actual_products)

    return render_template("checkout.html", products=actual_products, total=total, form=form)



@app.route("/confirm_order", methods=["POST", "GET"])
def confirm_order():
    form = OrderForm()
    cart = session.get('cart', [])

    actual_products = Product.query.filter(Product.id.in_(cart)).all()
    all_products_names = ", ".join([product.name for product in actual_products])
    total_price = sum(product.price for product in actual_products)

    if form.validate_on_submit():

        name = form.name.data
        address = form.address.data
        phone = form.phone.data


        new_order = Order(
            name=name,
            address=address,
            phone=phone,
            items=all_products_names,
            total_price=total_price
        )


        db.session.add(new_order)
        db.session.commit()

        session.pop('cart', None)
        flash("შეკვეთა წარმატებით გაფორმდა!", "success")
        return redirect("/")


    return render_template("checkout.html", form=form, total=total_price, products=actual_products)


@app.route("/author")
def authors():
    authors = Author.query.all()

    return render_template("Authors.html", authors=authors)




@app.route("/authors_detailed/<author_name>")
def author_detailed(author_name):
    author = Author.query.filter_by(name=author_name).first()
    author_books = Product.query.filter_by(author=author.name).all()
    return render_template("authors_detailed.html", author=author, products=author_books)


@app.route("/add_author", methods=["GET", "POST"])
@login_required
def add_author():
    form = AuthorForm()
    if form.validate_on_submit():
        new_author = Author(name=form.name.data, bio=form.bio.data)
        db.session.add(new_author)

        image = form.image.data
        img_location = os.path.join(app.root_path, "static", "images", image.filename)
        image.save(img_location)

        new_author.image = image.filename

        db.session.add(new_author)
        db.session.commit()

        flash("ავტორი წარმატებით დაემატა!", "success")
        return redirect("/author")

    return render_template("add_author.html", form=form)



@app.route("/delete_author/<int:author_id>")
@login_required
def delete_author(author_id):
    author = Author.query.get(author_id)

    db.session.delete(author)
    db.session.commit()

    flash("ავტორი წარმატებით წაიშალა", "danger")
    return redirect("/")




@app.route("/edit_author/<int:author_id>", methods=["POST", "GET"])
@login_required
def edit_author(author_id):
    author = Author.query.get(author_id)
    form = AuthorForm(name=author.name, bio=author.bio)

    if form.validate_on_submit():
        author.name = form.name.data
        author.bio = form.bio.data

        if form.image.data:
            image_file = form.image.data
            filename = image_file.filename
            image_file.save(f"static/images/{filename}")
            author.image = filename

        db.session.commit()

        flash("ავტორი წარმატებით განახლდა!", "success")
        return redirect("/")

    return render_template("add_author.html", form=form)





@app.route("/search")
def search():
    query = request.args.get('query')
    if query:
        products = Product.query.filter(Product.name.contains(query) | Product.description.contains(query)).all()
    else:
        products = []

    return render_template('search_results.html', products=products, query=query)


@app.route("/search_author")
def search_author():
   query = request.args.get("query")
   if query:
        authors = Author.query.filter(Author.name.contains(query)).all()
   else:
        authors = []

   return render_template('search_author.html', authors=authors, query=query)


@app.route("/add_review/<int:product_id>", methods=["POST"])
@login_required
def add_review(product_id):
    content = request.form.get("content")
    rating = request.form.get("rating")


    if rating:
        new_review = Review(
            content=content,
            rating=int(rating),
            user_id=current_user.id,
            product_id=product_id
        )


        db.session.add(new_review)
        db.session.commit()

    return redirect(f"/detailed/{product_id}")


@app.route("/delete_review/<int:review_id>", methods=["POST"])
@login_required
def delete_review(review_id):
    review = Review.query.get(review_id)

    db.session.delete(review)
    db.session.commit()

    flash("კომენტარი წარმატებით წაიშალა", "danger")
    return redirect(request.referrer)




@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ChangePasswordForm()

    if form.validate_on_submit():

        if current_user.check_password(form.old_password.data):

            new_hashed_password = generate_password_hash(form.new_password.data)
            current_user.password = new_hashed_password

            db.session.commit()

            flash("პაროლი წარმატებით შეიცვალა!", "success")
            return redirect("/profile")
        else:
            flash("ძველი პაროლი არასწორია!", "danger")


    return render_template("profile.html", form=form)

