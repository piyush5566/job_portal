function handleSearch(event) {
    event.preventDefault();
    
    const company = document.getElementById('company').value;
    const category = document.getElementById('category').value;
    const location = document.getElementById('location').value;
    
    // Show loading state
    const resultsContainer = document.getElementById('resultsContainer');
    resultsContainer.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    document.getElementById('searchResults').style.display = 'block';

    // Make AJAX request
    fetch(`/jobs/search?company=${encodeURIComponent(company)}&category=${encodeURIComponent(category)}&location=${encodeURIComponent(location)}`)
        .then(response => response.json())
        .then(data => {
            if (data.jobs.length === 0) {
                resultsContainer.innerHTML = '<div class="text-center">No jobs found matching your criteria.</div>';
                return;
            }

            // Create HTML for jobs
            const jobsHtml = data.jobs.map(job => `
                <div class="job-item p-4 mb-4">
                    <div class="row g-4">
                        <div class="col-sm-12 col-md-8 d-flex align-items-center">
                            <img class="flex-shrink-0 img-fluid border rounded" 
                                src="/static/${job.company_logo}" 
                                alt="${job.company} logo"
                                style="width: 80px; height: 80px; object-fit: cover;">
                            <div class="text-start ps-4">
                                <h5 class="mb-3"><a href="/jobs/${job.id}" class="text-dark">${job.title}</a></h5>
                                <span class="text-truncate me-3"><i class="fa fa-building text-primary me-2"></i>${job.company}</span>
                                <span class="text-truncate me-3"><i class="fa fa-map-marker-alt text-primary me-2"></i>${job.location}</span>
                                <span class="text-truncate me-0"><i class="far fa-money-bill-alt text-primary me-2"></i>${job.salary || 'Not specified'}</span>
                            </div>
                        </div>
                        <div class="col-sm-12 col-md-4 d-flex flex-column align-items-start align-items-md-end justify-content-center">
                            <div class="d-flex mb-3">
                                <a class="btn btn-primary" href="/jobs/${job.id}">View Details</a>
                            </div>
                            <small class="text-truncate"><i class="far fa-calendar-alt text-primary me-2"></i>Posted: ${new Date(job.posted_date).toLocaleDateString()}</small>
                        </div>
                    </div>
                </div>
            `).join('');
            
            resultsContainer.innerHTML = jobsHtml;
        })
        .catch(error => {
            console.error('Error:', error);
            resultsContainer.innerHTML = '<div class="alert alert-danger">An error occurred while searching for jobs. Please try again.</div>';
        });
}