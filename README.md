# Unified Web Service Portal

This project is aimed at providing a unified web service portal for multiple users and management teams.

## Getting Started
We use PDM as our package manager. Other package managers might be work, but not officially supported.

Please create your project with PDM:
```bash
pdm init
```

Then install the dependencies:
```bash
pdm add https://github.com/baobao1270/portal.git
```

Next, you can initialize the project with the following command:
```bash
pdm run portal-build init
```

## Development Server & Build
We have a built-in development server for you to test your code. You can start the development server with the following command:
```bash
pdm run portal-build serve
```

**Note: don't use the development server in production environment, or you will have security issues.**

When you have done the development, you can build the project with the following command:
```bash
pdm run portal-build build
```

This will generate static files to the dist directory (by default the path is `dist`). Then, you can deploy the static files to your web server.

You may also need remove `.html` suffix from the URL. A tipical Nginx configuration is:

```nginx
location / {
    try_files $uri $uri/ $uri.html =404;
}
```

## Development
Clone this repository and install the dependencies:
```bash
git clone https://github.com/baobao1270/portal.git
cd portal
pdm install
```

**Note: you may fork this repository and clone your forked repository.**

Then you'd better update CSS files with the following command:
```bash
pdm run update-css
```

Now you can start development.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
