/**
 * Task Tracker plugin functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const taskTableBody = document.getElementById('taskTableBody');
    const emptyTaskList = document.getElementById('emptyTaskList');
    const taskList = document.getElementById('taskList');
    const newTaskBtn = document.getElementById('newTaskBtn');
    const emptyNewTaskBtn = document.getElementById('emptyNewTaskBtn');
    const taskModal = document.getElementById('taskModal');
    const taskModalTitle = document.getElementById('taskModalTitle');
    const taskForm = document.getElementById('taskForm');
    const taskId = document.getElementById('taskId');
    const taskTitle = document.getElementById('taskTitle');
    const taskDescription = document.getElementById('taskDescription');
    const taskStatus = document.getElementById('taskStatus');
    const taskPriority = document.getElementById('taskPriority');
    const taskDueDate = document.getElementById('taskDueDate');
    const saveTaskBtn = document.getElementById('saveTaskBtn');
    const filterStatusLinks = document.querySelectorAll('.filter-status');
    
    // Bootstrap Modal instance
    let modal;
    
    // Current filter
    let currentFilter = 'all';
    
    // Initialize
    function init() {
        // Initialize Bootstrap modal
        modal = new bootstrap.Modal(taskModal);
        
        // Load tasks
        loadTasks();
        
        // Event listeners
        newTaskBtn.addEventListener('click', showNewTaskModal);
        emptyNewTaskBtn.addEventListener('click', showNewTaskModal);
        saveTaskBtn.addEventListener('click', saveTask);
        
        // Filter status links
        filterStatusLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                currentFilter = this.dataset.status;
                loadTasks();
            });
        });
    }
    
    // Load tasks from API
    function loadTasks() {
        fetch('/plugins/task-tracker/tasks')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    displayTasks(data.data);
                } else {
                    app.showNotification(data.message || 'Failed to load tasks', 'danger');
                }
            })
            .catch(error => {
                console.error('Error loading tasks:', error);
                app.showNotification('An error occurred while loading tasks', 'danger');
            });
    }
    
    // Display tasks in the table
    function displayTasks(tasks) {
        // Filter tasks if needed
        if (currentFilter !== 'all') {
            tasks = tasks.filter(task => task.status === currentFilter);
        }
        
        // Clear table
        taskTableBody.innerHTML = '';
        
        // Show empty state if no tasks
        if (tasks.length === 0) {
            taskList.classList.add('d-none');
            emptyTaskList.classList.remove('d-none');
            return;
        }
        
        // Show task list
        emptyTaskList.classList.add('d-none');
        taskList.classList.remove('d-none');
        
        // Add tasks to table
        tasks.forEach(task => {
            const row = document.createElement('tr');
            
            // Format date strings
            const createdDate = new Date(task.created_at).toLocaleDateString();
            const dueDate = task.due_date ? new Date(task.due_date).toLocaleDateString() : '-';
            
            // Status badge
            let statusBadge = 'bg-secondary';
            if (task.status === 'completed') {
                statusBadge = 'bg-success';
            } else if (task.status === 'in-progress') {
                statusBadge = 'bg-blue';
            } else if (task.status === 'pending') {
                statusBadge = 'bg-yellow';
            }
            
            // Priority badge
            let priorityBadge = 'bg-secondary';
            if (task.priority === 'high') {
                priorityBadge = 'bg-red';
            } else if (task.priority === 'medium') {
                priorityBadge = 'bg-orange';
            } else if (task.priority === 'low') {
                priorityBadge = 'bg-green';
            }
            
            // Build row HTML
            let rowHtml = `
                <td>
                    <div class="font-weight-medium">${task.title}</div>
                    <div class="text-muted">${task.description || ''}</div>
                </td>
                <td><span class="badge ${statusBadge}">${task.status}</span></td>
                <td><span class="badge ${priorityBadge}">${task.priority}</span></td>
            `;
            
            // Add due date column if enabled
            if (taskDueDate) {
                rowHtml += `<td>${dueDate}</td>`;
            }
            
            // Add created date and actions
            rowHtml += `
                <td>${createdDate}</td>
                <td>
                    <div class="btn-list flex-nowrap">
                        <button type="button" class="btn btn-sm btn-outline-primary edit-task-btn" data-task-id="${task.id}">
                            <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                                <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                                <path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1"></path>
                                <path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z"></path>
                                <path d="M16 5l3 3"></path>
                            </svg>
                            Edit
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger delete-task-btn" data-task-id="${task.id}">
                            <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                                <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                                <path d="M4 7h16"></path>
                                <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"></path>
                                <path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"></path>
                                <path d="M10 12l4 4m0 -4l-4 4"></path>
                            </svg>
                            Delete
                        </button>
                    </div>
                </td>
            `;
            
            row.innerHTML = rowHtml;
            taskTableBody.appendChild(row);
            
            // Add event listeners for edit and delete buttons
            row.querySelector('.edit-task-btn').addEventListener('click', () => {
                editTask(task);
            });
            
            row.querySelector('.delete-task-btn').addEventListener('click', () => {
                deleteTask(task.id);
            });
        });
    }
    
    // Show new task modal
    function showNewTaskModal() {
        taskModalTitle.textContent = 'New Task';
        taskForm.reset();
        taskId.value = '';
        
        // Set default priority
        const defaultPriority = document.body.dataset.defaultPriority || 'medium';
        taskPriority.value = defaultPriority;
        
        modal.show();
    }
    
    // Show edit task modal
    function editTask(task) {
        taskModalTitle.textContent = 'Edit Task';
        taskId.value = task.id;
        taskTitle.value = task.title;
        taskDescription.value = task.description || '';
        taskStatus.value = task.status;
        taskPriority.value = task.priority;
        
        if (taskDueDate && task.due_date) {
            const dueDateObj = new Date(task.due_date);
            const formattedDate = dueDateObj.toISOString().split('T')[0];
            taskDueDate.value = formattedDate;
        }
        
        modal.show();
    }
    
    // Save task (create or update)
    function saveTask() {
        // Validate form
        if (!taskTitle.value.trim()) {
            app.showNotification('Task title is required', 'warning');
            return;
        }
        
        // Prepare task data
        const taskData = {
            title: taskTitle.value.trim(),
            description: taskDescription.value.trim(),
            status: taskStatus.value,
            priority: taskPriority.value
        };
        
        // Add due date if present
        if (taskDueDate && taskDueDate.value) {
            taskData.due_date = taskDueDate.value;
        }
        
        // Determine if creating or updating
        const isEditing = taskId.value !== '';
        const url = isEditing 
            ? `/plugins/task-tracker/tasks/${taskId.value}`
            : '/plugins/task-tracker/tasks';
        const method = isEditing ? 'PUT' : 'POST';
        
        // Get CSRF token
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        // Send request
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(taskData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                app.showNotification(data.message || 'Task saved successfully', 'success');
                modal.hide();
                loadTasks();
            } else {
                app.showNotification(data.message || 'Failed to save task', 'danger');
            }
        })
        .catch(error => {
            console.error('Error saving task:', error);
            app.showNotification('An error occurred while saving the task', 'danger');
        });
    }
    
    // Delete task
    function deleteTask(id) {
        if (!confirm('Are you sure you want to delete this task?')) {
            return;
        }
        
        // Get CSRF token
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        fetch(`/plugins/task-tracker/tasks/${id}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                app.showNotification(data.message || 'Task deleted successfully', 'success');
                loadTasks();
            } else {
                app.showNotification(data.message || 'Failed to delete task', 'danger');
            }
        })
        .catch(error => {
            console.error('Error deleting task:', error);
            app.showNotification('An error occurred while deleting the task', 'danger');
        });
    }
    
    // Initialize the plugin
    init();
});