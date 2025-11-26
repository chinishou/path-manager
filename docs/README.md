# Path Manager Documentation

Complete documentation for Path Manager.

## Quick Links

- [Main README](../README.MD) - Project overview and quick start
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Examples](EXAMPLES.md) - Practical usage examples
- [Deployment Guide](DEPLOYMENT.md) - Production deployment
- [Schema Guide](SCHEMA_GUIDE.md) - Writing schemas
- [Contributing](CONTRIBUTING.md) - Contribution guidelines
- [Platform Schemas](../examples/PLATFORM_SCHEMAS.md) - Platform-specific schemas

## Documentation Structure

### Getting Started

1. **[Main README](../README.MD)** - Start here
   - Features overview
   - Installation
   - Quick start guide
   - Platform-specific schemas
   - Basic usage examples

2. **[Platform Schemas Guide](../examples/PLATFORM_SCHEMAS.md)**
   - Linux vs Windows vs cross-platform
   - Schema selection guide
   - Platform recommendations

### Core Documentation

3. **[Schema Writing Guide](SCHEMA_GUIDE.md)** - How to write schemas
   - Schema basics
   - Fields, directories, filenames, kinds
   - Best practices
   - Common patterns
   - Validation

4. **[API Reference](API_REFERENCE.md)** - Complete API documentation
   - Compiler API
   - Resolver API
   - ResolvedPath API
   - Store API
   - Structure Manager API
   - Exceptions

5. **[Examples](EXAMPLES.md)** - Practical usage examples
   - Basic usage
   - VFX pipeline examples
   - Game development examples
   - Platform-specific usage
   - Advanced patterns
   - Error handling
   - Integration examples (Flask, CLI)

### Deployment & Operations

6. **[Deployment Guide](DEPLOYMENT.md)** - Production deployment
   - NFS deployment
   - CI/CD integration (GitHub Actions, GitLab CI, Jenkins)
   - Platform-specific deployment
   - High availability
   - Monitoring
   - Troubleshooting

### Contributing

7. **[Contributing Guide](CONTRIBUTING.md)** - How to contribute
   - Development setup
   - Making changes
   - Testing
   - Code style
   - Pull request process
   - Bug reports and feature requests

## By Topic

### For New Users

- [Main README](../README.MD) - Start here
- [Quick Start](../README.MD#quick-start)
- [Examples - Basic Usage](EXAMPLES.md#basic-usage)

### For Schema Authors

- [Schema Guide](SCHEMA_GUIDE.md)
- [Platform Schemas](../examples/PLATFORM_SCHEMAS.md)
- [Schema Validation](SCHEMA_GUIDE.md#validation)

### For Developers

- [API Reference](API_REFERENCE.md)
- [Examples](EXAMPLES.md)
- [Contributing](CONTRIBUTING.md)

### For DevOps/SysAdmins

- [Deployment Guide](DEPLOYMENT.md)
- [NFS Setup](DEPLOYMENT.md#nfs-deployment)
- [CI/CD Integration](DEPLOYMENT.md#cicd-integration)
- [Monitoring](DEPLOYMENT.md#monitoring)

### For Pipeline TDs

- [VFX Pipeline Examples](EXAMPLES.md#vfx-pipeline-examples)
- [Advanced Patterns](EXAMPLES.md#advanced-patterns)
- [Structure Manager](API_REFERENCE.md#structure-manager-api)

### For Game Developers

- [Game Development Examples](EXAMPLES.md#game-development-examples)
- [Asset Bundle Management](EXAMPLES.md#example-7-asset-bundle-organization)
- [Level Management](EXAMPLES.md#example-8-level-data-management)

## Common Tasks

### Writing a Schema

1. Read [Schema Guide](SCHEMA_GUIDE.md)
2. Choose [platform](../examples/PLATFORM_SCHEMAS.md)
3. Follow [best practices](SCHEMA_GUIDE.md#best-practices)
4. Use [validation](SCHEMA_GUIDE.md#validation)

### Deploying to Production

1. Read [Deployment Guide](DEPLOYMENT.md)
2. Set up [NFS](DEPLOYMENT.md#nfs-deployment)
3. Configure [CI/CD](DEPLOYMENT.md#cicd-integration)
4. Set up [monitoring](DEPLOYMENT.md#monitoring)

### Integrating into Application

1. Read [API Reference](API_REFERENCE.md)
2. Check [examples](EXAMPLES.md)
3. See [integration examples](EXAMPLES.md#integration-examples)

### Contributing Code

1. Read [Contributing Guide](CONTRIBUTING.md)
2. Set up [development environment](CONTRIBUTING.md#development-setup)
3. Follow [code style](CONTRIBUTING.md#code-style)
4. Submit [pull request](CONTRIBUTING.md#pull-request-process)

## Support

- **Documentation Issues**: Open issue with "docs" label
- **Questions**: Check docs first, then open issue
- **Bug Reports**: See [Bug Reporting](CONTRIBUTING.md#reporting-bugs)
- **Feature Requests**: See [Feature Requests](CONTRIBUTING.md#suggesting-features)

## Offline Reading

### Generate PDF

```bash
# Install pandoc
sudo apt-get install pandoc

# Generate PDF
pandoc docs/*.md -o path-manager-docs.pdf --toc
```

### Generate HTML

```bash
# Install mkdocs
pip install mkdocs mkdocs-material

# Serve locally
mkdocs serve

# Build static site
mkdocs build
```

## Changelog

See [Git History](https://github.com/your-repo/path-manager/commits/main) for detailed changelog.

## Version

This documentation is for Path Manager version **0.1.0**.

Last updated: 2024-01-15
