// Add log sanitization to protect sensitive data
function sanitizeLogData(data, sensitiveFields = ['password', 'token', 'secret', 'key', 'authorization']) {
  if (!data || typeof data !== 'object') return data;
  
  const result = { ...data };
  
  for (const field of sensitiveFields) {
    if (field in result) {
      result[field] = '********';
    }
  }
  
  // Also check nested objects
  for (const key in result) {
    if (typeof result[key] === 'object' && result[key] !== null) {
      result[key] = sanitizeLogData(result[key], sensitiveFields);
    }
  }
  
  return result;
}

// Update createAppLogger to use sanitization
function createAppLogger(config = {}) {
  // ... existing code ...
  
  // Add sanitization configuration
  const sensitiveFields = config.sensitiveFields || ['password', 'token', 'secret', 'key', 'authorization'];
  
  // Create a custom format that sanitizes log data
  const sanitizeFormat = format((info) => {
    return sanitizeLogData(info, sensitiveFields);
  });
  
  // Update the logger format to include sanitization
  const logger = createLogger({
    level: options.logLevel,
    format: combine(
      timestamp(),
      errors({ stack: true }),
      sanitizeFormat(),  // Add sanitization
      json()
    ),
    // ... rest of the configuration ...
  });
  
  // ... rest of the function ...
} 