# Horilla HRMS

[![License: LGPL v2.1](https://img.shields.io/badge/License-LGPL%20v2.1-blue.svg)](https://www.gnu.org/licenses/lgpl-2.1)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-5.0+-green.svg)](https://www.djangoproject.com/)
[![Stars](https://img.shields.io/github/stars/horilla-opensource/horilla)](https://github.com/horilla-opensource/horilla/stargazers)
[![Forks](https://img.shields.io/github/forks/horilla-opensource/horilla)](https://github.com/horilla-opensource/horilla/network/members)

> **A comprehensive, free, and open-source Human Resource Management System (HRMS) designed to streamline HR operations and enhance organizational efficiency.**

## 🚀 Features

### Core HR Modules
- 👥 **Employee Management** - Centralized workforce data with LDAP integration
- 🎯 **Recruitment** - End-to-end hiring process from job posting to onboarding
- 📋 **Onboarding & Offboarding** - Structured workflows for employee lifecycle
- ⏰ **Attendance & Time Tracking** - Biometric integration and automated check-in/out
- 🏖️ **Leave Management** - Policy enforcement, approvals, and balance tracking
- 💰 **Payroll** - Automated salary processing, tax calculations, and compliance
- 📊 **Performance Management** - Goal setting, reviews, and continuous feedback
- 🏢 **Asset Management** - Track and manage company resources
- 🎫 **Helpdesk** - Centralized HR support and ticketing system


## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [Security](#-security)
- [Support](#-support)
- [License](#-license)

## ⚡ Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone -b release/v2.0.0-beta https://github.com/horilla-opensource/horilla.git
cd horilla

# Start with Docker Compose
docker-compose up -d

# Access the application
open http://localhost:8000
```

### Manual Installation

```bash
# Clone and setup
git clone -b release/v2.0.0-beta https://github.com/horilla-opensource/horilla.git
cd horilla

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.dist .env
# Edit .env with your configuration

# Initialize database
python manage.py migrate
python manage.py compilemessages
python manage.py collectstatic

# Run development server
python manage.py runserver
```


## 🛠 Installation

For detailed installation instructions, configuration guides, and platform-specific setup instructions, please visit our comprehensive documentation:

### 📖 [Complete Installation Guide → docs.horilla.com/technical/v2.0/ ](https://docs.horilla.com/technical/v2.0/)

Our documentation includes:
- **Step-by-step installation** for all supported platforms
- **Database configuration** guides
- **Environment setup** instructions
- **Production deployment** best practices
- **Troubleshooting** common issues
- **Advanced configuration** options

<!-- Need help? Check out the [Installation FAQ](https://docs.horilla.com) or reach out to our [community support](#-support). -->

## 🚀 Deployment

For production deployment guides including Nginx, Apache, and cloud platforms:
### 📖 [Deployment Guide → docs.horilla.com/technical/v2.0/doc/deployment/nginx-gunicorn](https://docs.horilla.com/technical/v2.0/doc/deployment/nginx-gunicorn)


## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Fork and clone your fork
git clone -b release/v2.0.0-beta https://github.com/YOUR_USERNAME/horilla.git
cd horilla

# Add upstream remote
git remote add upstream https://github.com/horilla-opensource/horilla.git

# Create feature branch
git checkout -b feature/your-feature-name

# Install development dependencies
pip install -r requirements.txt

# Submit pull request
```

### Code Standards

- Follow [PEP 8](https://pep8.org/) for Python code
- Use [Black](https://black.readthedocs.io/) for code formatting
- Write tests for new features
- Update documentation for user-facing changes

## 🔒 Security

### Security Features

- 🔐 **Authentication & Authorization** - Role-based access control
- 🛡️ **Data Protection** - Encrypted sensitive data storage
- 🔍 **Audit Trails** - Comprehensive activity logging
- 🚫 **Input Validation** - XSS and injection protection
- 🔒 **Session Security** - Secure session management

### Reporting Security Issues

Please report security vulnerabilities to **support@horilla.com**. Do not create public GitHub issues for security vulnerabilities.

### Security Best Practices

- Always use HTTPS in production
- Regularly update dependencies
- Use strong passwords and enable 2FA
- Monitor logs for suspicious activities

## 📞 Support

### Community Support

- 📖 **Documentation**: [docs.horilla.com](https://docs.horilla.com)
- 💬 **GitHub Discussions**: [GitHub Discussions](https://github.com/horilla-opensource/horilla/discussions)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/horilla-opensource/horilla/issues)
- ✨ **Feature Requests**: [GitHub Issues](https://github.com/horilla-opensource/horilla/issues)

### Professional Support

For enterprise support, custom development, and consulting services:
- 📧 **Email**: support@horilla.com
- 🌐 **Website**: [www.horilla.com](https://www.horilla.com)


## 📄 License

This project is licensed under the [LGPL-2.1 License](LICENSE) - see the LICENSE file for details.

<div align="center">

**Made with ❤️ by the Horilla Team**

[⭐ Star us on GitHub](https://github.com/horilla-opensource/horilla) | [🐛 Report Bug](https://github.com/horilla-opensource/horilla/issues) | [💡 Request Feature](https://github.com/horilla-opensource/horilla/issues)

</div>
