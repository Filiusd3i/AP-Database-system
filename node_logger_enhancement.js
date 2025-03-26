// Add state transition tracking
function logStateTransition(logger, entity, fromState, toState, metadata = {}) {
  logger.info(`State transition: ${entity} changed from ${fromState} to ${toState}`, {
    type: 'state_transition',
    entity,
    from_state: fromState,
    to_state: toState,
    ...metadata
  });
}

// Example
logStateTransition(logger, 'Order', 'pending', 'processing', { 
  orderId: 'ORD-123', 
  triggeredBy: 'payment_service' 
}); 