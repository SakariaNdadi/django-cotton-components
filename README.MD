# Django Cotton Components

A collection of pre-built, stylish, and functional form components to streamline your Django development process.

## Key Features:

- Pre-built Components: Quickly add common form elements like text inputs, textareas, select boxes, and more.
- Alpine.js for Interactivity: Leverage Alpine.js to add dynamic behavior to your components without relying on full-fledged JavaScript frameworks.
- Easy to Use: Simple installation and configuration, allowing you to focus on building your application.

## Dependencies:

- [Django-Cotton](https://django-cotton.com/)
- [AlpineJs](https://alpinejs.dev/)
- [TailwindCSS](https://tailwindcss.com/) (optional)

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

## DISCLAIMER

The package is under active development. More changes will occur. The package is not yet stable. When using it and run into issues and/or have suggestions please create an ISSUE on [GITHUB](https://github.com/SakariaNdadi/django-cotton-components)

## Inheritance

In your 'templates' directory, create a cotton directory.

example: create `input.html`

```html
<c-dcc-input class="styling classes" errorTimer="1000" />
```

In your project reference your component, `<c-input id="thisInput" type="date" />`.

## Components

By default some components come with TailwindCSS styling.

### Headers

```html
<c-dcc-h title="" class="" url="" {{ attrs }}>`extra content`</c-dcc-h>
```

By default it is a `h1`, no styling is provided.

- id: Unique identifier for the input.
- class: Customise to your preference add your own.
- url: If provided, the heading becomes a link.

### Input

```html
<c-dcc-input
	id=""
	class=""
	type=""
	errorTimer=""
	borderErrorClass=""
	errorDivClass=""
	validationUrl=""
	{{attrs}}
/>
```

By default it is a text input if no type is provided..

- id: Unique identifier for the input.
- class: Customise to your preference add your own.
- type: By default this is text. Define your type (date, email, number, etc.).
- errorTimer: If variable is not passed the form errors will show indefinitely. Pass milliseconds to prop to display how long the error will be displayed for.
- validationUrl: Requires [HTMX](https://htmx.org/). This will validate your input such as username, checkout [example](https://youtu.be/yf7_txKvexk?si=WAuxBFEfnrqmCYWp).
- attrs: Do not reference attrs. Add extra attributes such as 'name', 'value', 'placeholder', 'required' etc.

### Textarea

```html
<c-dcc-textarea
	id=""
	class=""
	errorTimer=""
	errorDivClass=""
	validationUrl=""
	{{attrs}}
/>
```

- id: Unique identifier for the input.
- errorTimer: If variable is not passed the form errors will show indefinitely. Pass milliseconds to prop to display how long the error will be displayed for.
- validationUrl: Requires [HTMX](https://htmx.org/). This will validate your input such as username, checkout [example](https://youtu.be/yf7_txKvexk?si=WAuxBFEfnrqmCYWp).
- attrs: Do not reference attrs. Add extra attributes such as 'name', 'value', 'placeholder', 'rows' etc.

### Password Input

```html
<c-dcc-password-input id="" name="" show {{ attrs }} />
```

- id: Unique identifier for the password input.
- show: Enables password visibility toggle.
- attrs: Do not reference attrs. Add extra attributes such as 'name', 'value', 'placeholder', 'required' etc.

### Button

```html
<c-dcc-button id="" class="" title="" icon="" svg="" url="" />
```

- id: Unique identifier for the button.
- class: Add styling to your button.
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
<c-dcc-select
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
<c-dcc-select-multiple
	id=""
	label=""
	name=""
	:options="[]"
	:data=""
	:values=""
/>
```

- id: Unique identifier for the select.
- label: Label displayed above the select.
- options: Array of options to be displayed in the select.
- data: Data passed from your view ( `cars = Car.objects.all()` ).
- values: When provided, the component checks each item in the values array against the data (e.g, an array of objects) and marks the matching options as selected.

Note: Being worked on, display of selected options when using ':data' not on par with ':options'

### Checkbox

```html
<c-dcc-checkbox id="" label="" description="" value="" />
```

- id: Unique identifier for the checkbox.
- label: Label displayed above the checkbox.
- description: displayed below the checkbox.
- value: Value to be passed when clicked.

### Toggle

```html
<c-dcc-toggle id="" label="" value="" />
```

- id: Unique identifier for the toggle.
- label: Label displayed above the toggle.
- value: Value to be passed when toggled.

### Radio

```html
<c-dcc-radio id="" label="" description="" value="" />
```

- id: Unique identifier for the radio.
- label: Label displayed above the radio.
- description: displayed below the radio.
- value: Value to be passed when clicked.

### Modal

```html
<c-dcc-modal
	id=""
	buttonClass=""
	modalClass=""
	headerClass=""
	headerLabelClass=""
	bodyClass=""
	header=""
	label=""
>
	<!-- Your content -->
</c-dcc-modal>
```

- header: Header text for the modal.
- label: Label for the modal toggle.

### Table

```html
<c-dcc-table
	id=""
	:th="[]"
	thClass=""
	:tr=""
	trClass=""
	paginate_by=""
	search
/>
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

- You can add other attributes to the components such as `aria-label` etc.
- You can also add custom attributes to the components to suit your needs such as HTMX.
- Read more about [{{ attrs }}](https://django-cotton.com/docs/components#attrs)

### Mentions

- [Penguin](https://www.penguinui.com/) components.
- [BugBytes](https://www.youtube.com/@bugbytes3923) educational content.
