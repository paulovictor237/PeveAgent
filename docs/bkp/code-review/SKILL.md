# Simple Code Review

Quick code review skill that checks PRs against your custom rules.

## Usage

Just ask Claude:
- "Review PR #123"

- "Check PR #456 for issues"
- "Look at PR #789"

## Your Custom Rules

Check for these patterns in the code:

### 🔴 Critical Issues

**Eloquent update/delete without get/first**
- Pattern: `->update()` or `->delete()` without `->first()`, `->get()`, or `->find()` before it
- Why: Can update/delete multiple records unintentionally
- Example bad: `User::where('id', $id)->update(['status' => 'active']);`
- Example good: `User::where('id', $id)->first()->update(['status' => 'active']);`

**SQL raw with concatenation**
- Pattern: `DB::raw()` or `whereRaw()` with variables concatenated in string
- Why: SQL injection risk
- Example bad: `DB::raw("status = '$status'")`
- Example good: `DB::raw('status = ?', [$status])`

**Mass assignment with request->all()**
- Pattern: `->create($request->all())` or `->update($request->all())`
- Why: Mass assignment vulnerability
- Example bad: `User::create($request->all());`
- Example good: `User::create($request->validated());`

**Blade unescaped output**
- Pattern: `{!! $variable !!}` in .blade.php files
- Why: XSS vulnerability
- Example bad: `{!! $user->bio !!}`
- Example good: `{{ $user->bio }}`

### 🟡 High Priority

**N+1 Query Problem**
- Pattern: Accessing relationships inside foreach loop
- Why: Generates one query per item
- Example bad: `foreach ($posts as $post) { echo $post->author->name; }`
- Example good: `$posts = Post::with('author')->get(); foreach ...`

**Routes without auth middleware**
- Pattern: `Route::post/put/patch/delete` without `->middleware(['auth'])`
- Why: Unauthenticated users can modify data
- Example bad: `Route::post('/users', [UserController::class, 'store']);`
- Example good: `Route::post('/users', ...)->middleware(['auth']);`

**Controller without validation**
- Pattern: Controller method using `Request $request` without validation
- Why: Unvalidated input
- Example bad: `public function store(Request $request) { User::create(...); }`
- Example good: `public function store(StoreUserRequest $request) { ... }`

### 🟠 Medium Priority

**env() outside config/**
- Pattern: `env('KEY')` used outside config/ directory
- Why: Won't work when config is cached
- Example bad: `$key = env('API_KEY');` in a controller
- Example good: `$key = config('services.api_key');`

**Debug code left in**
- Pattern: `dd()`, `dump()`, `var_dump()`, `print_r()`
- Why: Debug code should be removed
- Example bad: `dd($user);`
- Example good: Remove it or use `Log::debug(...)`

**API POST route without custom Request class**
- Pattern: `Route::post()` in routes/api.php with controller method using generic `Request $request`
- Why: API POST endpoints must validate input with custom FormRequest classes
- Example bad: `public function store(Request $request)` for POST route
- Example good: `public function store(CreateCheckinRequest $request)`
- Note: Custom Request class should match the action, like `CreateCheckinRequest`, `UpdateUserRequest`, etc.

**API response without Resource**
- Pattern: Controller returning data without using API Resource (`return response()->json($data)` or `return $data`)
- Why: API responses must be formatted through Resources for consistency
- Example bad: `return response()->json($checkin);` or `return $checkin;`
- Example good: `return CheckinResource::make($checkin);`
- CRITICAL: Resource should NOT be inside `response()->json()` - that's wrong!
- Example WRONG: `return response()->json(CheckinResource::make($checkin));`
- Example RIGHT: `return CheckinResource::make($checkin);`

**Database queries outside Repositories**
- Pattern: Eloquent queries (`Model::where()`, `Model::find()`, `DB::table()`, etc.) used outside Repository classes
- Why: All database queries must be in Repository classes for clean architecture
- Example bad: `User::where('email', $email)->first();` in a Controller or Service
- Example good: Move to `UserRepository` and call `$this->userRepository->findByEmail($email);`
- Note: Controllers and Services should never query the database directly

**DTO not using ValidatedDTO**
- Pattern: Custom DTO classes that don't extend `WendellAdriel\ValidatedDTO\ValidatedDTO`
- Why: All DTOs must use the ValidatedDTO library for consistency and validation
- Example bad: `class UserData { public string $name; }`
- Example good: `use WendellAdriel\ValidatedDTO\ValidatedDTO; class UserData extends ValidatedDTO { ... }`
- Note: Check if DTO file has `use WendellAdriel\ValidatedDTO\ValidatedDTO;` and `extends ValidatedDTO`

### 📝 Commit Messages

**Non-conventional commit messages**
- Pattern: Commit messages that don't follow Conventional Commits format
- Why: Consistency and automated changelog generation
- Format: `type: description` where type is: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert
- Example bad: `updated user controller`, `fixes`, `WIP`
- Example good: `feat: add create checkin endpoint`, `fix: resolve token expiration issue`, `refactor: move queries to repository`
- Note: Scope is optional but recommended. Breaking changes should have `!` or `BREAKING CHANGE:` in footer

## How to Review

When user asks to review a PR:

1. Use `bash_tool` to get the PR commits:
   ```bash
   gh pr view <PR_NUMBER> --json commits --jq '.commits[].messageHeadline'
   ```

2. Use `bash_tool` to get the PR diff:
   ```bash
   gh pr diff <PR_NUMBER>
   ```

3. Check commit messages against Conventional Commits pattern

4. Look through the diff for the code patterns above

5. Tell the user in chat what you found:
   ```
   Found 2 issues in PR #123:
   
   🔴 app/Services/UserService.php (line 42)
   - Using ->update() without ->first()
   - This can update multiple records: User::where('email', $email)->update([...])
   - Fix: Add ->first() before ->update()
   
   🟡 app/Http/Controllers/PostController.php (line 28)
   - Possible N+1 query in foreach loop
   - Consider using eager loading: Post::with('author')->get()
   ```

4. Keep it conversational and helpful, not automated/robotic

## Important

- Only report real issues you actually see in the diff
- Be brief and conversational
- Don't generate a huge formal report
- Just point out problems naturally in chat
- If no issues found, just say "Looks good, didn't see any of our common issues"

## Add Your Own Rules

To add new rules, just add them to this file in the same format:

```
**Your rule name**
- Pattern: what to look for
- Why: why it's a problem  
- Example bad: code showing the problem
- Example good: code showing the fix
```