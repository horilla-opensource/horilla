const mix = require('laravel-mix');

// mix.js('static/src/js/index.js', 'static/build/js/web.frontend.min.js')
mix.sass('static/src/scss/main.scss', 'css/style.min.css')
    .postCss('static/src/css/tailwind.css', 'css/tailwind.css', [
        require('tailwindcss'),
        require('autoprefixer'),
    ])
    .postCss('static/src/css/login.css', 'css/login.css', [
        require('tailwindcss')('./tailwind.login.config.js'),
        require('autoprefixer'),
    ]);

mix.setPublicPath('static/build');
