/* eslint-disable @typescript-eslint/no-explicit-any */
import { Box, Typography } from "@mui/material";

export function WorkflowApprovals() {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Approvals</Typography>
      <Typography variant="body2" color="text.secondary">
        Pending workflow step approvals will appear here
      </Typography>
    </Box>
  );
}
