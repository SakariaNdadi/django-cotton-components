# Django Cotton Components

A collection of pre-built, stylish, and functional form components to streamline your Django development process.

## Key Features:

- Pre-built Components: Quickly add common form elements like text inputs, textareas, select boxes, and more.
- Tailwind CSS Integration: Seamlessly integrate with your existing Tailwind CSS setup for consistent styling.
- Alpine.js for Interactivity: Leverage Alpine.js to add dynamic behavior to your components without relying on full-fledged JavaScript frameworks.
- Easy to Use: Simple installation and configuration, allowing you to focus on building your application.

## Dependencies:

- [Django-Cotton](https://django-cotton.com/)
- [AlpineJs](https://alpinejs.dev/)
- [TailwindCSS](https://tailwindcss.com/)

## Installation:

```python

    pip install django-cotton-components

```

- Follow the [Django-Cotton](https://django-cotton.com/docs/quickstart#install) installation steps.
- Add [AlpineJs](https://alpinejs.dev/) and its plugins(collapse, focus, mask).
- Add [TailwindCSS](https://tailwindcss.com/).

#### Add to installed apps

```python

    INSTALLED_APPS = [
        ...
        "django_cotton",
        "django_cotton_components",
        ...
    ]

```

## Components

### Headers

```html
<c-h1 title="Testing H1">`extra content`</c-h1>
<c-h2 title="Testing H2">`extra content`</c-h2>
<c-h3 title="Testing H3">`extra content`</c-h3>
<c-h4 title="Testing H4">`extra content`</c-h4>
```

### Input

```html
<c-input id="" class="" type="" errorTimer="" validationUrl="" {{ attrs }} />
```

By default it is a text input if no type is provided.

- id: Unique identifier for the input.
- class: By default this uses TailwindCSS, to customise to your preference add your own.
- type: By default this is text. Define your type (date, email, number, etc.).
- errorTimer: If variable is not passed the form errors will show indefinitely. Pass milliseconds to prop to display how long the error will be displayed for.
- validationUrl: Requires [HTMX](https://htmx.org/). This will validate your input such as username, checkout [example](https://youtu.be/yf7_txKvexk?si=WAuxBFEfnrqmCYWp).
- attrs: Do not reference attrs. Add extra attributes such as 'name', 'value', 'placeholder', 'required' etc.

### Textarea

```html
<c-textarea id="" class="" errorTimer="" validationUrl="" {{ attrs }} />
```

- id: Unique identifier for the input.
- errorTimer: If variable is not passed the form errors will show indefinitely. Pass milliseconds to prop to display how long the error will be displayed for.
- validationUrl: Requires [HTMX](https://htmx.org/). This will validate your input such as username, checkout [example](https://youtu.be/yf7_txKvexk?si=WAuxBFEfnrqmCYWp).
- attrs: Do not reference attrs. Add extra attributes such as 'name', 'value', 'placeholder', 'rows' etc.

### Password Input

```html
<c-password-input id="" name="" show {{ attrs }} />
```

- id: Unique identifier for the password input.
- show: Enables password visibility toggle.
- attrs: Do not reference attrs. Add extra attributes such as 'name', 'value', 'placeholder', 'required' etc.

### Button

```html
<c-button id="" title="Testing" icon="" svg="" url="" />
```

- id: Unique identifier for the button.
- title: Button text.
- type: Button type(submit, reset etc.).
- url: If provided, the button renders as `<a href="...">` otherwise, it renders as `<button>`.

##### Icon or SVG not both

- icon: Icon name to be displayed on the button.
- svg: Path to an SVG icon.

##### Extra

You can add extra attributes on the button, example, `<c-button id="" title="Testing" hx-get="some_url" hx-trigger="click" hx-target="#some_id" />`

### Select options

##### Single Select

```html
<c-select
	id=""
	name=""
	:options="['Option1','Option2']"
	:data="cars"
	search
	value=""
/>
```

- id: Unique identifier for the select.
- options: Array of options to be displayed in the select.
- data: Data passed from your view ( `cars = Car.objects.all()` ).
- search: Enables search functionality.
- value: When provided, the component checks each item in the values array against the data (e.g, an array of objects) and marks the matching options as selected.

Note: If you use ':data' and no data is provided an 'IndexError' will be produced.

##### MultiSelect

```html
<c-select-multiple id="" label="" name="" :options="[]" :data="" :values="" />
```

- id: Unique identifier for the select.
- label: Label displayed above the select.
- options: Array of options to be displayed in the select.
- data: Data passed from your view ( `cars = Car.objects.all()` ).
- values: When provided, the component checks each item in the values array against the data (e.g, an array of objects) and marks the matching options as selected.

Note: Being worked on, display of selected options when using ':data' not on par with ':options'

### Checkbox

```html
<c-checkbox id="" label="" description="" value="" />
```

- id: Unique identifier for the checkbox.
- label: Label displayed above the checkbox.
- description: displayed below the checkbox.
- value: Value to be passed when clicked.

### Toggle

```html
<c-toggle id="" label="" value="" />
```

- id: Unique identifier for the toggle.
- label: Label displayed above the toggle.
- value: Value to be passed when toggled.

### Radio

```html
<c-radio id="" label="" description="" value="" />
```

- id: Unique identifier for the radio.
- label: Label displayed above the radio.
- description: displayed below the radio.
- value: Value to be passed when clicked.

### Modal

```html
<c-modal id="" header="" label="">
	<!-- Your content -->
</c-modal>
```

- header: Header text for the modal.
- label: Label for the modal toggle.

### Table

```html
<c-table id="" :th="[]" thClass="" :tr="" trClass="" paginate_by="" search />
```

- id: Unique identifier for the table.
- th: Array of column names that specify which data fields will display.
- thClass: Custom class for `<thead>` styling.
- tr: Data from the view (must be a list of dictionaries).
  Example:<br>
  `cars = Car.objects.all()`<br>
  `context={"table_cars":list(cars.values())}`
- trClass: Custom class for <tr> row styling.
- paginate_by: Number of rows displayed per page.
- search: Enables search functionality across the specified columns in :th.

## Attributes

- You can add your own `class=""` to any of the components to suit your css, example Bootstrap.
- You can add other attributes to the components such as `aria-label` etc.
- You can also add custom attributes to the components to suit your needs such as HTMX.

### Mentions

- [Penguin](https://www.penguinui.com/) components.
- [BugBytes](https://www.youtube.com/@bugbytes3923) educational content.
