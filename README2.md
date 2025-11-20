# Bank Fraud Detection System

A comprehensive bank statement fraud detection system that uses anomaly detection, LLM-based analysis, and automated reporting to identify suspicious transactions and document modifications.

## 🏗️ Project Structure

```
BankFraudDetection/
├── .env                    # Environment variables (API keys)
├── anomaly.py             # Anomaly detection algorithms
├── app.py                 # Main application entry point
├── config.py              # Configuration and settings management
├── graph.py               # Visualization and graphing utilities
├── pdf_checks.py          # PDF integrity validation
├── pdf_loader.py          # PDF parsing and data extraction
├── report.py              # Report generation module
├── run_detection.py       # Detection pipeline orchestration
├── schemas.py             # Data validation schemas
├── validators.py          # Input validation logic
├── requirements.txt       # Python dependencies
├── backend/
│   └── main.py           # Backend API server
├── frontend/
│   ├── src/
│   │   ├── App.jsx       # Main React component
│   │   ├── main.jsx      # React entry point
│   │   └── styles.css    # Application styles
│   ├── index.html        # HTML template
│   ├── package.json      # Node.js dependencies
│   └── vite.config.js    # Vite configuration
├── reports/               # Generated fraud detection reports
│   ├── PDF_Bank_Statement1.pdf_report.md
│   └── statement_aug.md
└── samples/               # Sample JSON documents for testing
    ├── sample_valid_doc.json
    └── sample_suspicious_doc.json
```

## 🚀 Features

- **Anomaly Detection**: Statistical analysis to identify unusual transaction patterns
- **LLM-Powered Analysis**: Uses Groq API for intelligent fraud detection
- **PDF Processing**: Extract and validate bank statements from PDF files
- **Automated Reporting**: Generate detailed markdown reports of findings
- **REST API**: Backend API for integration with frontend or external systems
- **Interactive Frontend**: React-based UI for visualizing results
- **Document Validation**: Detect modifications and tampering in PDF documents

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+ (for frontend)
- Groq API key

## 🔧 Installation

### Backend Setup

1. Clone the repository and navigate to the project directory

2. Install Python dependencies:
```sh
pip install -r requirements.txt
```

3. Configure environment variables:
   - Create a [`.env`](.env) file in the root directory
   - Add your Groq API key:
   ```
   GROQ_API_KEY="your_api_key_here"
   ```

4. Run the backend server:
```sh
python backend/main.py
```

### Frontend Setup

1. Navigate to the frontend directory:
```sh
cd frontend
```

2. Install dependencies:
```sh
npm install
```

3. Start the development server:
```sh
npm run dev
```

The frontend will be available at `http://localhost:5173`

## ⚙️ Configuration

Configuration is managed through [`config.py`](config.py) which loads settings from the [`.env`](.env) file:

- `GROQ_API_KEY`: Your Groq API key for LLM analysis (required)
- `llm_model`: Model to use (default: "openai/gpt-oss-20b")
- `enable_llm`: Enable/disable LLM-based detection (default: true)

Example configuration in [`config.py`](config.py):
```python
class Settings(BaseModel):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    llm_model: str = "openai/gpt-oss-20b"
    enable_llm: bool = True
```

## 🎯 Usage

### Running Detection

Execute the fraud detection pipeline:
```sh
python run_detection.py
```

### Running the Main Application

Start the main application:
```sh
python app.py
```

### Analyzing PDFs

Process bank statement PDFs:
```sh
python pdf_loader.py <path_to_pdf>
```

### Generating Reports

Reports are automatically generated in the [`reports/`](reports/) directory after detection runs. Example reports:
- [`PDF_Bank_Statement1.pdf_report.md`](reports/PDF_Bank_Statement1.pdf_report.md)
- [`statement_aug.md`](reports/statement_aug.md)

## 📊 Sample Data

Sample documents are provided in the [`samples/`](samples/) directory:
- [`sample_valid_doc.json`](samples/sample_valid_doc.json): Example of a valid bank statement
- [`sample_suspicious_doc.json`](samples/sample_suspicious_doc.json): Example with suspicious patterns

These samples can be used for testing the detection algorithms and understanding the expected data format.

## 🔍 Key Components

### Core Modules

- **[`anomaly.py`](anomaly.py)**: Implements statistical anomaly detection algorithms for identifying unusual transaction patterns
- **[`pdf_checks.py`](pdf_checks.py)**: Validates PDF integrity and detects modifications or tampering
- **[`pdf_loader.py`](pdf_loader.py)**: Parses PDF bank statements and extracts transaction data
- **[`validators.py`](validators.py)**: Input validation and data sanitization logic
- **[`schemas.py`](schemas.py)**: Pydantic models for data validation and type checking
- **[`graph.py`](graph.py)**: Data visualization utilities for transaction analysis
- **[`report.py`](report.py)**: Generates detailed fraud detection reports in Markdown format
- **[`config.py`](config.py)**: Centralized configuration management using environment variables

### Application Entry Points

- **[`app.py`](app.py)**: Main application entry point
- **[`run_detection.py`](run_detection.py)**: Detection pipeline orchestration
- **[`backend/main.py`](backend/main.py)**: REST API server

### Frontend

- **[`frontend/src/App.jsx`](frontend/src/App.jsx)**: Main React component
- **[`frontend/src/main.jsx`](frontend/src/main.jsx)**: React application entry point
- **[`frontend/src/styles.css`](frontend/src/styles.css)**: Application styling
- **[`frontend/vite.config.js`](frontend/vite.config.js)**: Vite bundler configuration

## 🛠️ Technology Stack

### Backend
- Python 3.8+
- Pydantic for data validation
- Groq API for LLM-based fraud detection
- PDF processing libraries

### Frontend
- React
- Vite for fast development and building
- Modern ES6+ JavaScript

## ⚠️ Security Notes

**Important Security Considerations:**

1. **API Key Protection**: The [`.env`](.env) file contains sensitive API keys and should **NEVER** be committed to version control
2. **Add to .gitignore**: Ensure `.env` is listed in your `.gitignore` file
3. **Key Rotation**: Regularly rotate your Groq API key
4. **Environment Variables**: Use environment-specific `.env` files for different deployment environments

Create a `.gitignore` file if it doesn't exist:
```
.env
__pycache__/
node_modules/
dist/
*.pyc
```

## 📝 Development

### Running Tests

```sh
# Run Python tests
python -m pytest

# Run frontend tests
cd frontend
npm test
```

### Code Style

Follow PEP 8 guidelines for Python code and ESLint rules for JavaScript/React code.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is provided as-is for fraud detection purposes.

## 🐛 Troubleshooting

### Common Issues

**API Key Not Found**
- Ensure your [`.env`](.env) file is in the root directory
- Verify the `GROQ_API_KEY` is set correctly
- Run `python -c "from config import settings; print(settings.groq_api_key)"` to test

**Module Not Found**
- Install all dependencies: `pip install -r requirements.txt`
- Ensure you're using the correct Python environment

**Frontend Not Starting**
- Navigate to [`frontend/`](frontend/) directory
- Run `npm install` to install dependencies
- Check that Node.js 16+ is installed

## 📞 Support

For issues or questions, please review the existing reports in [`reports/`](reports/) for examples of the system's output and capabilities.
```
