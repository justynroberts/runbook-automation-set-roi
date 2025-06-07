#!/usr/bin/env python3

import requests
import json
import sys
from typing import Dict, List, Optional, Union

# =============================================================================
# CONFIGURATION - Update these values for your environment
# =============================================================================

# Runtime configuration
DRY_RUN = True  # Set to False to apply changes
PROJECT_FILTER = "all"  # Set to specific project name or "all"

# Default configuration - override with environment variables
RUNDECK_URL = ""  # Set via RUNDECK_URL environment variable
API_TOKEN = ""    # Set via RUNDECK_API_TOKEN environment variable

# ROI Metrics configuration
DEFAULT_HOURS_SAVED = 2.0  # Default value for hours field

# API configuration
API_VERSION = "46"  # Rundeck API version to use
ROI_PLUGIN_NAME = None  # Auto-detected on first run

# =============================================================================

class RundeckROIManager:
    def __init__(self, rundeck_url: str, api_token: str):
        """
        Initialize the Rundeck ROI manager
        
        Args:
            rundeck_url: Base URL of your Rundeck instance (e.g., 'https://rundeck.company.com')
            api_token: Your Rundeck API token
        """
        self.base_url = rundeck_url.rstrip('/')
        self.api_token = api_token
        self.roi_plugin_name = None  # Will be auto-detected
        self.headers = {
            'X-Rundeck-Auth-Token': api_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def get_projects(self) -> List[Dict]:
        """Get all projects from Rundeck"""
        url = f"{self.base_url}/api/{API_VERSION}/projects"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print("Timeout error: The request took too long to complete")
            return []
        except requests.exceptions.ConnectionError:
            print("Connection error: Could not connect to Rundeck server")
            return []
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred: {e}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error fetching projects: {e}")
            return []
    
    def get_project_jobs(self, project_name: str) -> List[Dict]:
        """Get all jobs for a specific project"""
        url = f"{self.base_url}/api/{API_VERSION}/project/{project_name}/jobs"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print(f"Timeout error: The request for project {project_name} took too long")
            return []
        except requests.exceptions.ConnectionError:
            print(f"Connection error: Could not connect to Rundeck server for project {project_name}")
            return []
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred for project {project_name}: {e}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error fetching jobs for project {project_name}: {e}")
            return []
    
    def get_job_definition(self, job_id: str) -> Optional[Dict]:
        """Get job definition from Rundeck"""
        url = f"{self.base_url}/api/{API_VERSION}/job/{job_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            job_def = response.json()
            # API returns a list with a single job definition
            if isinstance(job_def, list) and len(job_def) > 0:
                return job_def[0]
            return job_def
        except requests.exceptions.Timeout:
            print(f"Timeout error: The request for job {job_id} took too long")
            return None
        except requests.exceptions.ConnectionError:
            print(f"Connection error: Could not connect to Rundeck server for job {job_id}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred for job {job_id}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching job definition for {job_id}: {e}")
            return None
    
    def detect_roi_plugin_name(self, job_def: Union[Dict, List[Dict]]) -> Optional[str]:
        """
        Auto-detect the ROI plugin name from a job definition
        
        Args:
            job_def: Job definition dictionary or list from Rundeck API
            
        Returns:
            Optional[str]: Name of ROI plugin if found, None otherwise
        """
        # Handle list format
        if isinstance(job_def, list):
            if not job_def or not isinstance(job_def[0], dict):
                return None
            job_def = job_def[0]
            
        if not isinstance(job_def, dict):
            return None
            
        plugins = job_def.get('plugins', {})
        if not isinstance(plugins, dict):
            return None
            
        execution_plugins = plugins.get('ExecutionLifecycle', {})
        if not isinstance(execution_plugins, dict):
            return None
        
        for plugin_name in execution_plugins.keys():
            if 'roi' in plugin_name.lower() and 'metric' in plugin_name.lower():
                return plugin_name
        
        return None
    
    def ensure_roi_plugin_name(self) -> bool:
        """
        Ensure we have the ROI plugin name by checking existing jobs
        
        Returns:
            bool: True if ROI plugin name was found or already set, False otherwise
        """
        if self.roi_plugin_name:
            return True
        
        print("Auto-detecting ROI plugin name...")
        
        # Get first project and job to detect plugin name
        projects = self.get_projects()
        if not projects:
            print("No projects found")
            return False
        
        for project in projects[:3]:  # Check first few projects
            project_name = project.get('name')
            if not project_name:
                continue
                
            jobs = self.get_project_jobs(project_name)
            if not jobs:
                continue
            
            for job in jobs[:5]:  # Check first few jobs
                job_id = job.get('id')
                if not job_id:
                    continue
                    
                job_def = self.get_job_definition(job_id)
                if job_def:
                    detected_name = self.detect_roi_plugin_name(job_def)
                    if detected_name:
                        self.roi_plugin_name = detected_name
                        print(f"Detected ROI plugin name: {detected_name}")
                        return True
        
        print("Could not auto-detect ROI plugin name")
        return False
    
    def validate_job_data(self, job_data: Dict) -> bool:
        """Validate job data before sending to API"""
        # Check if job_data is valid
        if not job_data or not isinstance(job_data, dict):
            print(f"❌ Invalid job data: {type(job_data)}")
            return False
            
        required_fields = ['name']
        
        for field in required_fields:
            if field not in job_data:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Validate plugins structure if present
        if 'plugins' in job_data:
            plugins = job_data['plugins']
            if plugins is None:
                # Remove None plugins to avoid issues
                job_data.pop('plugins', None)
            elif not isinstance(plugins, dict):
                print(f"❌ Invalid plugins structure: must be dict, got {type(plugins)}")
                return False
            else:
                if 'ExecutionLifecycle' in plugins:
                    exec_plugins = plugins['ExecutionLifecycle']
                    if exec_plugins is None:
                        # Remove None ExecutionLifecycle to avoid issues
                        plugins.pop('ExecutionLifecycle', None)
                    elif not isinstance(exec_plugins, dict):
                        print(f"❌ Invalid ExecutionLifecycle structure: must be dict, got {type(exec_plugins)}")
                        return False
        
        return True
    
    def update_job(self, project_name: str, job_id: str, job_data: Dict) -> bool:
        """Update job definition in Rundeck"""
        # Validate job_data is not None
        if not job_data or not isinstance(job_data, dict):
            print(f"❌ Invalid job data for {job_id}: {type(job_data)}")
            return False
        
        # Create job context for better logging
        job_name = job_data.get('name', 'Unknown')
        job_context = f"[{project_name}] {job_name}"
        
        # Check if job already has ROI plugin and update it, otherwise add new one
        if not self.update_existing_roi_plugin(job_data, job_context):
            if not self.add_roi_metrics_plugin(job_data, job_context):
                print(f"❌ Failed to add ROI metrics plugin for {job_id}")
                return False
        
        # Clean up the job data for update - remove fields that shouldn't be in update
        update_data = job_data.copy()
        
        # Remove fields that cause issues with job updates
        fields_to_remove = ['id', 'href', 'permalink', 'averageDuration', 'project']
        for field in fields_to_remove:
            update_data.pop(field, None)
        
        # Validate the job data
        if not self.validate_job_data(update_data):
            print(f"❌ Job data validation failed for {job_id}")
            return False
        
        # Try import method first as it's more reliable for complex updates
        return self._update_job_via_import(project_name, job_id, update_data)
    
    def _update_job_via_import(self, project_name: str, job_id: str, job_data: Dict) -> bool:
        """Alternative method to update job via import API"""
        url = f"{self.base_url}/api/{API_VERSION}/project/{project_name}/jobs/import"
        params = {
            'dupeOption': 'update',
            'format': 'json'
        }
        
        # Ensure required fields are present for import
        if 'name' not in job_data:
            print(f"❌ Job data missing required 'name' field for import")
            return False
            
        try:
            response = requests.post(url, headers=self.headers, json=[job_data], params=params, timeout=30)
            
            if response.status_code in [200, 204]:
                return True
            else:
                print(f"Failed to import job. Status Code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error importing job {job_id}: {e}")
            return False
    
    def has_hours_field(self, job_def: Dict) -> tuple:
        """
        Check if job already has a hours field in ROI Metrics
        Returns (has_field, value) tuple
        """
        try:
            if not job_def or not isinstance(job_def, dict):
                return False, None
                
            plugins = job_def.get('plugins', {})
            if not plugins or not isinstance(plugins, dict):
                return False, None
                
            execution_plugins = plugins.get('ExecutionLifecycle')
            if not execution_plugins or not isinstance(execution_plugins, dict):
                return False, None
            
            # Look for ROI Metrics Data plugin
            for plugin_name, plugin_config in execution_plugins.items():
                if not isinstance(plugin_config, dict):
                    continue
                    
                if (self.roi_plugin_name and plugin_name == self.roi_plugin_name) or \
                   ('roi' in plugin_name.lower() and 'metric' in plugin_name.lower()):
                    
                    # Check if hours field exists in various formats
                    fields = plugin_config.get('fields', [])
                    
                    # Handle JSON string format
                    if isinstance(fields, str):
                        try:
                            fields = json.loads(fields)
                        except json.JSONDecodeError:
                            continue
                    
                    if isinstance(fields, list):
                        for field in fields:
                            if isinstance(field, dict):
                                field_key = field.get('key', '').lower()
                                if 'hours' in field_key:
                                    return True, field.get('value', 'unknown')
                            elif isinstance(field, str) and 'hours' in field.lower():
                                return True, 'unknown'
                    
                    # Check userRoiData field which might contain the fields
                    user_roi_data = plugin_config.get('userRoiData')
                    if isinstance(user_roi_data, str):
                        try:
                            roi_fields = json.loads(user_roi_data)
                            if isinstance(roi_fields, list):
                                for field in roi_fields:
                                    if isinstance(field, dict):
                                        field_key = field.get('key', '').lower()
                                        if 'hours' in field_key:
                                            return True, field.get('value', 'unknown')
                        except json.JSONDecodeError:
                            pass
            
            return False, None
            
        except Exception as e:
            print(f"❌ Error checking for hours field: {e}")
            return False, None
    
    def add_roi_metrics_plugin(self, job_def: Dict, job_context: str = "") -> bool:
        """
        Add ROI Metrics Data plugin with hours field to job definition
        """
        try:
            # Validate job_def is not None and is a dict
            if not job_def or not isinstance(job_def, dict):
                print(f"❌ Invalid job definition: {type(job_def)}")
                return False
            
            if 'plugins' not in job_def:
                job_def['plugins'] = {}
            
            # Ensure plugins is a dict
            if not isinstance(job_def['plugins'], dict):
                job_def['plugins'] = {}
            
            if 'ExecutionLifecycle' not in job_def['plugins']:
                job_def['plugins']['ExecutionLifecycle'] = {}
            
            # Ensure ExecutionLifecycle is a dict
            if not isinstance(job_def['plugins']['ExecutionLifecycle'], dict):
                job_def['plugins']['ExecutionLifecycle'] = {}
            
            # Use the detected plugin name or fallback to default
            plugin_name = self.roi_plugin_name or "roi-metrics-data"
            
            # Create userRoiData field
            roi_data = [
                {
                    'key': 'hours',
                    'label': 'Hours Saved By automation',
                    'desc': 'Number of hours saved by this automation',
                    'value': str(DEFAULT_HOURS_SAVED)
                }
            ]
            
            # Add the ROI Metrics plugin with userRoiData
            job_def['plugins']['ExecutionLifecycle'][plugin_name] = {
                'userRoiData': json.dumps(roi_data)
            }
            
            context_msg = f" to {job_context}" if job_context else ""
            print(f"Added ROI plugin '{plugin_name}' with hours field{context_msg}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding ROI metrics plugin: {e}")
            return False
    
    def update_existing_roi_plugin(self, job_def: Dict, job_context: str = "") -> bool:
        """
        Update existing ROI Metrics plugin to include hours field
        Only updates if the field doesn't already exist
        """
        try:
            # Validate job_def is not None and is a dict
            if not job_def or not isinstance(job_def, dict):
                print(f"❌ Invalid job definition for ROI plugin update: {type(job_def)}")
                return False
            
            plugins = job_def.get('plugins', {})
            if not isinstance(plugins, dict):
                return False
                
            execution_plugins = plugins.get('ExecutionLifecycle', {})
            if not isinstance(execution_plugins, dict):
                return False
            
            for plugin_name, plugin_config in execution_plugins.items():
                if not isinstance(plugin_config, dict):
                    continue
                # Check for ROI plugin using the same logic as detection
                if (self.roi_plugin_name and plugin_name == self.roi_plugin_name) or \
                   ('roi' in plugin_name.lower() and 'metric' in plugin_name.lower()):
                    
                    print(f"Found existing ROI plugin: {plugin_name}")
                    
                    # Get existing userRoiData or create new
                    user_roi_data = plugin_config.get('userRoiData', '[]')
                    try:
                        roi_fields = json.loads(user_roi_data) if isinstance(user_roi_data, str) else []
                    except json.JSONDecodeError:
                        print(f"Warning: Invalid JSON in userRoiData, creating new: {user_roi_data}")
                        roi_fields = []
                    
                    # Check if hours field already exists
                    for field in roi_fields:
                        if isinstance(field, dict):
                            field_key = field.get('key', '').lower()
                            if 'hours' in field_key:
                                current_value = field.get('value', 'unknown')
                                print(f"Hours field already exists in ROI plugin ({current_value})")
                                return False  # Field already exists, no update needed
                    
                    # Add the hours field only if it doesn't exist
                    new_field = {
                        'key': 'hours',
                        'label': 'Hours Saved By automation',
                        'desc': 'Number of hours saved by this automation',
                        'value': str(DEFAULT_HOURS_SAVED)
                    }
                    
                    roi_fields.append(new_field)
                    plugin_config['userRoiData'] = json.dumps(roi_fields)
                    context_msg = f" for {job_context}" if job_context else ""
                    print(f"Added hours field to existing ROI plugin{context_msg}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error updating existing ROI plugin: {e}")
            return False
    
    def process_job_roi_metrics(self, job: Dict, project_name: str) -> bool:
        """
        Process a single job's ROI metrics configuration
        Returns True if changes were made, False otherwise
        """
        job_id = job.get('id')
        job_name = job.get('name', 'Unknown')
        
        # Get full job definition
        job_def = self.get_job_definition(job_id)
        if not job_def:
            print(f"❌ [{project_name}] {job_name} - Failed to retrieve definition")
            return False
        
        # Check if hours field already exists
        has_field, current_value = self.has_hours_field(job_def)
        if has_field:
            value_display = f"({current_value})" if current_value else ""
            print(f"✅ [{project_name}] {job_name} - Already has hours {value_display}")
            return False
            
        # Update the job with ROI metrics
        if self.update_job(project_name, job_id, job_def):
            print(f"🆕 [{project_name}] {job_name} - Added hours field")
            return True
        else:
            print(f"❌ [{project_name}] {job_name} - Failed to add hours field")
            return False
    
    def run(self, dry_run: bool = False, project_filter: str = "all"):
        """
        Main execution method
        
        Args:
            dry_run: If True, only shows what would be changed without making updates
            project_filter: Project name to process, or "all" for all projects
        """
        print("Runbook Automation ROI Status")
        print("-" * 30)
        print(f"Project: {project_filter}")
        print(f"Mode: {'Dry run' if dry_run else 'Update'}")
        print(f"Hours saved value: {DEFAULT_HOURS_SAVED}")
        print("-" * 30)
        
        # Auto-detect ROI plugin name if not already known
        if not self.ensure_roi_plugin_name():
            print("Error: Could not detect ROI plugin name. Make sure at least one job has ROI metrics configured.")
            return
        
        # Get all projects
        projects = self.get_projects()
        if not projects:
            print("No projects found or error occurred")
            return
        
        total_jobs_processed = 0
        total_jobs_updated = 0
        
        for project in projects:
            project_name = project.get('name')
            
            # Skip if not matching filter
            if project_filter.lower() != "all" and project_name.lower() != project_filter.lower():
                continue
                
            # Get all jobs for this project
            jobs = self.get_project_jobs(project_name)
            if not jobs:
                print(f"[{project_name}] No jobs found")
                continue
            
            for job in jobs:
                total_jobs_processed += 1
                
                if dry_run:
                    # In dry run, still check if job needs updating
                    job_name = job.get('name', 'Unknown')
                    job_def = self.get_job_definition(job.get('id'))
                    if job_def:
                        has_field, current_value = self.has_hours_field(job_def)
                        if has_field:
                            value_display = f"({current_value})" if current_value else ""
                            print(f"✅ [{project_name}] {job_name} - Already has hours {value_display}")
                        else:
                            print(f"🆕 [{project_name}] {job_name} - add hours [{DEFAULT_HOURS_SAVED}]")
                            total_jobs_updated += 1  # Count jobs that would be updated
                    else:
                        print(f"❌ [{project_name}] {job_name} - Could not retrieve job definition")
                else:
                    # Apply mode - actually process the job
                    if self.process_job_roi_metrics(job, project_name):
                        total_jobs_updated += 1
        
        print("\nSummary:")
        print(f"Projects: {len(projects)} | Jobs: {total_jobs_processed} | Updates: {total_jobs_updated}")
        if dry_run:
            print("\n⚠️  Dry run complete - use --apply to apply changes")

def validate_url(url: str) -> bool:
    """Validate the Rundeck URL format"""
    if not url:
        return False
    try:
        result = requests.utils.urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def main():
    # Read configuration from environment variables
    import os
    import argparse
    
    # Parse command line arguments to override defaults
    parser = argparse.ArgumentParser(description='Runbook Automation ROI Status - Manage ROI metrics for Rundeck jobs')
    parser.add_argument('--project', default=PROJECT_FILTER, help='Project name to process (default: all)')
    
    # Create mutually exclusive group for dryrun/apply
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--dryrun', action='store_true', help='Show what would be changed without applying (default)')
    mode_group.add_argument('--apply', action='store_true', help='Apply changes to jobs')
    
    args = parser.parse_args()
    
    # Determine dry_run mode - default to True unless --apply is specified
    dry_run = not args.apply
    
    # Get API credentials
    rundeck_url = os.getenv('RUNDECK_URL', RUNDECK_URL).strip()
    api_token = os.getenv('RUNDECK_API_TOKEN', API_TOKEN).strip()
    
    # Validate configuration
    if not rundeck_url:
        print("Error: Rundeck URL not set")
        print("Please set the RUNDECK_URL environment variable")
        sys.exit(1)
    
    if not api_token:
        print("Error: Rundeck API token not set")
        print("Please set the RUNDECK_API_TOKEN environment variable")
        sys.exit(1)
    
    if not validate_url(rundeck_url):
        print("Error: Invalid Rundeck URL format")
        print("URL must include protocol (http:// or https://) and hostname")
        sys.exit(1)
    
    # Initialize the manager
    manager = RundeckROIManager(rundeck_url, api_token)
    
    # Run with configured options
    manager.run(dry_run=dry_run, project_filter=args.project)

if __name__ == "__main__":
    main()