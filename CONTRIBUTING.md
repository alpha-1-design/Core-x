# Contributing to Core-x

First off, thank you for considering contributing to Core-x! It's people like you who help build better situational awareness for the world.

## How Can I Contribute?

### Reporting Bugs
*   Check the [Issues](https://github.com/alpha-1-design/Core-x/issues) to see if it's already reported.
*   Provide a clear description of the bug and steps to reproduce.
*   Include screenshots or logs from the browser console or Python server.

### Feature Requests
*   We are particularly interested in new **data sources** (e.g., weather, maritime traffic, social trends).
*   Open an issue with the "enhancement" label to discuss your idea.

### Pull Requests
1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/AmazingFeature`).
3.  Ensure your code follows PEP 8 for Python and standard JS conventions.
4.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
5.  Push to the branch (`git push origin feature/AmazingFeature`).
6.  Open a Pull Request.

## Engineering Standards

*   **Asynchronous Excellence:** Avoid blocking the main event loop in both Python and JS.
*   **Performance:** Three.js rendering should remain smooth (60 FPS) even with 1000+ markers.
*   **Data Integrity:** Always validate and sanitize external API data before broadcasting.

## Style Guide

*   **Python:** Use type hints and docstrings.
*   **JavaScript:** Prefer ES6+ features.
*   **CSS:** Use modular CSS or well-commented vanilla CSS.

Happy contributing!
